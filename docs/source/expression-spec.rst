.. _expression-spec:

表达式规范（Expression Specification）
=====================================

本文是 OneRoll 骰子表达式的规范正文：一套语法、一套语义。``1.x`` 现行语法是
正文里的正式定义；``2.0`` 的新特性并入同一组产生式和语义章节，逐项标注
「已实现／未实现（issue #N）」。

对齐版本：``dev @ 3b84ef2``（``3b84ef25610a``）。本文的产生式逐字引自该提交的
``src/oneroll/grammar.pest``（``1.x``）与 ``docs/rfcs/0001-v2-target.pest``
（``2.0`` 目标文法），语义引自 ``src/calculator.rs``、``src/errors.rs``、
``src/parser.rs``、``src/resource.rs``，示例期望值引自
``tests/conformance/v1.json``（46 条单表达式用例 + 5 条 program 用例）。凡标
``TODO`` 的地方表示本文未能从源码核实，需维护者确认。

写法约定
--------

* 正文以中文为主；规则名、产生式、错误码、API 名称保留英文原文。
* 每个语法/语义条目带状态标记：

  - **已实现**：``dev @ 3b84ef2`` 的解析器/求值器可运行，且有语料覆盖。
  - **未实现（issue #N）**：只存在于 RFC 或 issue，代码中尚不可用。
  - **TODO**：本文未能从源码核实。

* 产生式用 pest 风格（``~`` 连接、``|`` 有序选择、``?`` ``*`` ``+``、``@{…}``
  为 atomic、``_{…}`` 为 silent）。pest 是 PEG，选择是有序的：靠前的分支优先，
  因此长前缀必须排在短前缀之前（例如 ``ro`` 在 ``r`` 之前，见 3.3）。
* 表格里的「依据」列只引用仓库中真实存在的文件、规则或语料 ``id``。
  ``docs/rfcs/0001-v2-target.pest`` 是 **0001 号提案的附件**（与
  ``0001-dice-program-language-v2.rst`` 同属 0001，``git ls-tree 3b84ef2``
  可查），不是另一份 RFC；``docs/rfcs`` 下的提案只有 0001–0006。

1. 范围与术语
-------------

OneRoll 表达式求值产生一个 :class:`DiceResult`：``total``（整数）、
``flattened_rolls``（展平后的骰值个数）、``comment``（行尾注释文本）。
``1.x`` 的 ``roll`` 只接受一条指令；``2.0`` 的 ``Program`` 接受以 ``;`` 分隔的
多条指令，并共享一份执行预算。

术语对照：

* **factor（因子）**：不能再被运算符拆开的最小表达式单位，见 3.2。
* **选项 / 修饰符（option / modifier）**：绑定在骰子项之后的修饰语法。
  ``1.x`` 叫 modifier，``2.0`` 叫 option；两者共用 3.4 的记号表。
* **预算（budget）**：``src/resource.rs`` 里的资源上限，超出时报 ``limit.*``。

2. 词法
-------

2.1 ``1.x`` 词法（已实现）
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 16 10 52 22

   * - 记号
     - pest 修饰
     - 定义
     - 说明
   * - ``WHITESPACE``
     - ``_``
     - ``" " | "\t" | "\n" | "\r"``
     - 隐式空白：非 atomic 规则的 ``~`` 之间自动跳过
   * - ``number``
     - ``@``
     - ``"-"? ~ ("0" | '1'..'9' ~ '0'..'9'*)``
     - 有符号十进制整数；不允许前导零，不允许 ``+`` 号
   * - ``comment``
     - ``@``
     - ``"#" ~ (!"\n" ~ ANY)*``
     - 到行尾；``program`` 只允许一个，且必须在末尾
   * - ``d``
     - 字面量
     - ``"d"``
     - 骰子运算符；大小写敏感，只认小写 ``d``
   * - ``op``
     - 规则
     - ``"+" | "-" | "*" | "/" | "^"``
     - 五个标量运算符，全部同层（见 5.1）
   * - modifier 记号
     - 规则
     - ``! e K r ro R a k kh kl dh dl u s c``
     - 15 个，大小写敏感；``K``≠``k``、``R``≠``r``。完整表见 3.4

``number`` 是 atomic 规则，因此 ``- 1``（负号与数字之间有空白）不是合法数字；
``-2`` 是一个完整的因子。``dice_sides`` 也是 atomic，``1d -1`` 能解析成
``1d-1``（面数为 -1），这属于语义错误而不是语法错误，见 6 的
``zero_dice_sides``。

2.2 ``2.0`` 新增词法（未实现）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

以下记号来自 ``docs/rfcs/0001-v2-target.pest``，代码中尚未实现，分别由
issue #39（typed values / ranges / variables）、#40（weighted list dice）、
#51（表面语法）承载。

.. list-table::
   :header-rows: 1
   :widths: 18 46 18 18

   * - 记号
     - 定义
     - 状态
     - issue
   * - ``number``
     - ``@{ ASCII_DIGIT+ }``（无符号）
     - 未实现
     - #39
   * - ``signed_number``
     - ``@{ ("+" | "-")? ~ ASCII_DIGIT+ }``
     - 未实现
     - #39
   * - ``boolean``
     - ``{ ^"true" | ^"false" }``（大小写不敏感）
     - 未实现
     - #39
   * - ``string``
     - ``@{ "\"" ~ string_character* ~ "\"" }``；转义仅 ``\" \\ \n \r \t``，不允许裸换行
     - 未实现
     - #39
   * - ``identifier``
     - ``@{ (ASCII_ALPHA_LOWER | "_") ~ (ASCII_ALPHANUMERIC | "_")* }``
     - 未实现
     - #39
   * - ``dynamic_variable``
     - ``@{ "${" ~ (identifier | ASCII_DIGIT+) ~ "}" }``
     - 未实现
     - #39
   * - ``range``
     - ``{ "[" ~ signed_number ~ ".." ~ signed_number ~ "]" }``（闭区间）
     - 未实现
     - #39
   * - ``values_list``
     - ``{ "[" ~ (scalar_operand ~ ("," ~ scalar_operand)*)? ~ "]" }``（可空）
     - 未实现
     - TODO
   * - ``unique_value``
     - ``{ "u" }``，紧跟 ``d`` / ``l``（``^"l"``，大小写不敏感）表示不放回抽样
     - 未实现
     - #40
   * - ``weight_annotation``
     - ``{ "[" ~ number ~ percent_mark? ~ "]" }``（整数权重或百分比）
     - 未实现
     - #40

``2.0`` 的 ``WHITESPACE`` 只含空格、制表符与 ``NEWLINE``，**不含** ``\r``；
这与 ``1.x`` 的四字符集合不同，属于目标文法的既有事实，是否保留由 issue #51
一并讨论。

3. 语法
-------

3.1 程序与指令
~~~~~~~~~~~~~~~

``1.x``（已实现，``src/oneroll/grammar.pest``）：

.. code-block:: text

   program              = { SOI ~ instruction
                            ~ (instruction_separator ~ instruction)*
                            ~ comment? ~ EOI }
   instruction          = { dice_expr }
   instruction_separator = _{ ";" }

要点：``SOI``/``EOI`` 强制整串消费，所以 ``2 ** 3``、``1 +`` 这类残留输入会
整体报 ``parse.invalid_syntax``。``roll`` 只接受一条指令，``1; 2`` 报语法错误
（语料 ``multiple_instructions_in_roll``）；``program()`` 才执行多条。

``2.0``（未实现，issue #38 负责多指令 Program 在 Rust/Python/CLI 的落地）：

.. code-block:: text

   program              = { SOI ~ instruction
                            ~ (instruction_separator ~ instruction)*
                            ~ comment? ~ EOI }
   instruction_separator = _{ ";" }
   instruction          = { expression }
   comment              = @{ "#" ~ (!NEWLINE ~ ANY)* }

3.2 表达式分层与 factor（因子）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**``1.x``：单层、左结合，已实现。** 语法上只有一个二元层，没有优先级：

.. code-block:: text

   dice_expr = { dice_term ~ (op ~ dice_term)* }
   op        = { "+" | "-" | "*" | "/" | "^" }

   dice_term = { dice_roll | paren_expr | number }      (* factor *)
   paren_expr = { "(" ~ dice_expr ~ ")" }

``dice_term`` 就是 ``1.x`` 的 factor：三个分支——带修饰符的骰子、括号表达式、
整数字面量。因为只有一层，``dice_expr`` 在求值时按出现顺序从左到右折叠
（``src/calculator.rs`` 逐项 ``checked_*`` 归约）。由此：

* ``1 + 2 * 3`` = ``(1 + 2) * 3`` = ``9``（语料 ``flat_operator_precedence``
  用 ``1d1 + 2 * 3`` 固定了同一行为，``total = 9``）；
* ``2 ^ 3 ^ 2`` = ``(2 ^ 3) ^ 2`` = ``64``（语料 ``left_associative_power``）；
* ``-2 ^ 2`` = ``(-2) ^ 2`` = ``4``，负号属于 ``number`` 词法而不是前缀运算符。

**``2.0``：五层优先级，未实现（issue #16）。** 目标文法把表达式拍平成前缀序列，
由 Pratt parser 或等价 AST builder 还原优先级：

.. code-block:: text

   expression = { prefix_operator* ~ pipeline
                  ~ (scalar_operator ~ prefix_operator* ~ pipeline)* }
   pipeline   = { primary ~ option* }
   primary    = _{ parenthesized | function_call | dice | range | values_list
                 | dynamic_variable | boolean | number | string }

``2.0`` 的 factor 就是 silent 规则 ``primary``（文法里没有名为 ``factor`` 的
规则）。``option`` 不属于 factor，而是 ``pipeline`` 的一层，绑定到紧邻的前一个
primary，从左到右执行。RFC-0001 的层级从强到弱为：

1. 括号表达式与 primary pipeline；
2. ``**``（右结合）；
3. 前缀 ``+`` / ``-``；
4. ``*`` / ``/``（左结合）；
5. ``+`` / ``-``（左结合）。

按这套分层，``1 + 2 * 3`` = ``7``。这与 ``1.x`` 的 ``9`` 是**不兼容变更**：在
#16 落地前，``1.x`` 语义保持不变，本文以 5.1 为准。#16 的迁移说明由 issue #29
统一给出。

3.3 骰子与修饰符产生式
~~~~~~~~~~~~~~~~~~~~~~~

``1.x``（已实现，逐字引自 ``src/oneroll/grammar.pest``）：

.. code-block:: text

   dice_roll = { number ~ "d" ~ dice_sides ~ modifiers? }
   dice_sides = @{ number }
   modifiers = { modifier+ }
   modifier = {
       explode
     | explode_alias
     | explode_keep_high
     | reroll
     | reroll_once
     | reroll_until
     | reroll_add
     | keep_alias
     | keep_high
     | keep_low
     | drop_high
     | drop_low
     | unique
     | sort
     | count
   }
   explode           = { "!" }
   explode_alias     = { "e" }
   explode_keep_high = { "K" ~ number }
   reroll            = { "r" ~ number }
   reroll_once       = { "ro" ~ number }
   reroll_until      = { "R" ~ number }
   reroll_add        = { "a" ~ number }
   keep_alias        = { "k" ~ number }
   keep_high         = { "kh" ~ number }
   keep_low          = { "kl" ~ number }
   drop_high         = { "dh" ~ number }
   drop_low          = { "dl" ~ number }
   unique            = { "u" }
   sort              = { "s" }
   count             = { "c" ~ number }

注意规则名是 ``modifiers``/``modifier``、``reroll_add``（不是 ``dice_modifier``
或 ``reroll_and_add``）。``modifiers`` 无分隔符，可连写，如 ``2d6kh1s``。

**空白（WHITESPACE）判定。** ``WHITESPACE`` 是 silent 规则，pest 在所有非
atomic 规则的序列项之间自动插入 ``WHITESPACE*``；``number`` 与 ``dice_sides``
是 atomic 规则，只有它们**内部**不允许空白。由此词法层面的规范表述是：骰子
记号各字段之间是否允许空白，取决于承载它们的规则是否 atomic，本文**不**对
具体写法下等价结论——该行为目前没有 conformance 用例固定（见第 9 节 TODO，
建议补一条显式用例后再写进示例表）。

**``2.0`` 对应产生式（未实现）。** 目标文法里选项不再连写无参数，而是带
validator 或参数：

.. code-block:: text

   dice = _{ numeric_dice | list_dice }
   numeric_dice   = { scalar_operand? ~ ^"d" ~ unique_value? ~ (number | range) }
   list_dice      = { scalar_operand? ~ ^"l" ~ unique_value? ~ list_parameter }

   option = _{ keep_and_explode | reroll_until | reroll_and_add | keep | drop
             | filter | sort | count | reroll | explode | merge | bind
             | occurrences | unique | paint | conditional | split | group }
   low    = { "l" }
   keep   = { "k" ~ low? ~ number }
   drop   = { "d" ~ low? ~ number }
   keep_and_explode = { "K" ~ low? ~ number }
   filter = { "f" ~ scoped_validator }
   sort   = { "s" ~ low? }
   count  = { "c" ~ scoped_validator }
   reroll = { "r" ~ scoped_validator }
   reroll_until  = { "R" ~ scoped_validator }
   reroll_and_add = { "a" ~ scoped_validator }
   explode       = { "e" ~ scoped_validator }
   merge = { "m" ~ "(" ~ expression ~ ")" }
   bind  = { "b" }
   occurrences = { "o" ~ ("(" ~ number ~ ("," ~ occurrence_selector)? ~ ")")? }
   unique = { "u" }
   paint = { "p" ~ "[" ~ color_count ~ ("," ~ color_count)* ~ "]" }
   conditional = { "i" ~ scoped_validator ~ block ~ block? }
   split = { "y" }
   group = { "g" ~ number }

``2.0`` 取消了 ``1.x`` 的 ``!``、``e``（无参）与 ``ro``；``e`` 改为必须带
validator 的 explode，``r`` 也改为带 validator。是否保留 ``1.x`` 写法作为兼容
语法，是 issue #51 与 #29 的议题，本文不预设结论。

3.4 修饰符集合（唯一权威表）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

下表是本文唯一的修饰符清单，共 **15 条**，与 4.4 的语义表同序、同名、同集合；
其它章节只做交叉引用，不再列第二套别名表。

.. list-table::
   :header-rows: 1
   :widths: 8 16 12 20 26 18

   * - #
     - ``1.x`` 记号
     - 规则名
     - 参数
     - ``2.0`` 对应
     - 状态
   * - 1
     - ``!``
     - ``explode``
     - 无
     - ``e[validator]``
     - 已实现；``2.0`` 未实现（#24）
   * - 2
     - ``e``
     - ``explode_alias``
     - 无
     - 同上（``2.0`` 里 ``e`` 是唯一写法，必须带 validator）
     - 已实现；``2.0`` 未实现（#24）
   * - 3
     - ``K n``
     - ``explode_keep_high``
     - ``n``
     - ``K[l]n``
     - 已实现（但不 explode，#24）；``2.0`` 未实现（#24）
   * - 4
     - ``r n``
     - ``reroll``
     - ``n``
     - ``r[validator]``
     - 已实现；``2.0`` 未实现（#24）
   * - 5
     - ``ro n``
     - ``reroll_once``
     - ``n``
     - 兼容解析保留 ``ro``（RFC-0001「Compatibility parsing recognizes legacy
       ``ro`` before ``r``」）；target pest 无独立规则
     - 已实现；``2.0`` 未实现（#24 / #51）
   * - 6
     - ``R n``
     - ``reroll_until``
     - ``n``
     - ``R[validator]``
     - 已实现；``2.0`` 未实现（#24）
   * - 7
     - ``a n``
     - ``reroll_add``
     - ``n``
     - ``a[validator]``
     - 已实现；``2.0`` 未实现（#24）
   * - 8
     - ``k n``
     - ``keep_alias``
     - ``n``
     - ``k[l]n``
     - 已实现；``2.0`` 未实现（#15）
   * - 9
     - ``kh n``
     - ``keep_high``
     - ``n``
     - ``k n``
     - 已实现；``2.0`` 未实现（#15）
   * - 10
     - ``kl n``
     - ``keep_low``
     - ``n``
     - ``k l n``
     - 已实现；``2.0`` 未实现（#15）
   * - 11
     - ``dh n``
     - ``drop_high``
     - ``n``
     - ``d n``
     - 已实现；``2.0`` 未实现（#15）
   * - 12
     - ``dl n``
     - ``drop_low``
     - ``n``
     - ``d l n``
     - 已实现；``2.0`` 未实现（#15）
   * - 13
     - ``u``
     - ``unique``
     - 无
     - ``u``
     - 已实现；``2.0`` 未实现（#15）
   * - 14
     - ``s``
     - ``sort``
     - 无
     - ``s[l]``
     - 已实现；``2.0`` 未实现（#15）
   * - 15
     - ``c n``
     - ``count``
     - ``n``
     - ``c[validator]``
     - 已实现；``2.0`` 未实现（#15 / #41）

3.5 ``2.0`` 新增加的语法结构
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

以下全部**未实现**，产生式引自 ``docs/rfcs/0001-v2-target.pest``：

.. list-table::
   :header-rows: 1
   :widths: 20 58 10 12

   * - 结构
     - 产生式要点
     - 状态
     - issue
   * - 布尔 / 字符串 / 变量
     - ``boolean``、``string``、``dynamic_variable``（``${name}`` / ``${0}``）
     - 未实现
     - #39
   * - 闭区间
     - ``range = { "[" ~ signed_number ~ ".." ~ signed_number ~ "]" }``
     - 未实现
     - #39
   * - 值列表
     - ``values_list``，空 ``[]`` 合法
     - 未实现
     - TODO
   * - 数值区间骰
     - ``numeric_dice``，如 ``2d[1..6]``
     - 未实现
     - #40
   * - 加权列表骰
     - ``list_dice`` / ``list_parameter`` / ``weighted_item`` / ``weight_annotation``
     - 未实现
     - #40
   * - ``repeat``
     - ``repeat_call = { ^"repeat" ~ "(" ~ expression ~ ";" ~ instruction ~ (…)* ~ ")" }``
     - 未实现
     - #43
   * - 条件
     - ``conditional = { "i" ~ scoped_validator ~ block ~ block? }``
     - 未实现
     - #43
   * - validator
     - ``scoped_validator`` / ``validator_list`` / ``predicate``（见 5.3）
     - 未实现
     - #41
   * - 合并与标注
     - ``merge`` / ``bind`` / ``occurrences`` / ``paint`` / ``split`` / ``group``
     - 未实现
     - #42

``values_list`` 在现有 issue 里没有独立条目：它是 ``#40`` 列表骰与 ``#39`` 类型
系统的共用基础，归属待定，故标 ``TODO``。

4. 语义
-------

4.1 AST
~~~~~~~

``1.x``（已实现，``src/types.rs``）：

.. code-block:: text

   Expression   = Add | Subtract | Multiply | Divide | Power
                | Paren(Box<Expression>) | Number(i64) | DiceRoll(DiceRoll)
                | WithComment(Box<Expression>, Option<String>)

   DiceModifier = Explode | ExplodeAlias
                | ExplodeKeepHigh(i32) | Reroll(i32) | RerollOnce(i32)
                | RerollUntil(i32) | RerollAndAdd(i32)
                | KeepAlias(i32) | KeepHigh(i32) | KeepLow(i32)
                | DropHigh(i32) | DropLow(i32)
                | Unique | Sort | Count(i32)

``Paren`` 是显式 AST 节点（不是解析期消解），因此 ``(1 + 2) * 3`` 的括号语义
在 AST 里可追溯。``DiceModifier`` 的 15 个变体与 3.4 的 15 行一一对应；
``ExplodeAlias`` 是独立变体，不是 ``Explode`` 的解析期别名。

4.2 标量算术语义
~~~~~~~~~~~~~~~~~

``1.x``（已实现，``src/calculator.rs`` 的 ``evaluate_expression_node`` 与
``src/errors.rs``）：

.. list-table::
   :header-rows: 1
   :widths: 8 34 26 32

   * - 运算符
     - 语义
     - 错误码
     - Python 层异常
   * - ``+`` ``-`` ``*``
     - ``checked_add`` / ``checked_sub`` / ``checked_mul``（``i64``）
     - ``arithmetic.overflow``
     - ``ValueError``
   * - ``/``
     - ``checked_div``，向零截断：``5 / 2 = 2``、``-5 / 2 = -2``；
       ``i64::MIN / -1`` 溢出
     - 除零 ``arithmetic.divide_by_zero``；溢出 ``arithmetic.overflow``
     - ``ValueError``
   * - ``^``
     - ``checked_pow``，指数必须是 ``u32``；``0 ^ 0 = 1``
     - 指数为负或 > ``u32::MAX``：``arithmetic.invalid_exponent``；
       结果溢出：``arithmetic.overflow``
     - ``ValueError``
   * - ``Paren``
     - 仅分组，不求值副作用
     - 无
     - 无
   * - 多值聚合（``kh``/``c`` 等求和、计数）
     - ``checked_sum``；计数用 ``i64::try_from``
     - 溢出 ``arithmetic.overflow``
     - ``ValueError``

**Python 层映射（已实现，无 TODO）。** ``src/errors.rs`` 里
``impl From<DiceError> for pyo3::PyErr`` 把**所有** ``DiceError`` 统一转成
``ValueError``，并附加 ``_oneroll_error_json`` 属性（序列化后的
``ErrorEnvelope``）。因此 ``arithmetic.*``、``parse.*``、``limit.*`` 在 Python
里目前都是 ``ValueError``，只靠错误码区分。按领域细分异常层次是 issue #26
（未实现）。

4.3 骰子求值顺序
~~~~~~~~~~~~~~~~~

``1.x``（已实现，``roll_dice_with_budget``）分四个阶段，顺序由代码结构决定：

1. **逐骰、按源码顺序处理全部 ``!`` / ``e``**：每颗骰子掷出初值后，只要当前值
   等于面数就继续掷并追加，直到不相等。循环不受次数限制，只受预算约束。
   随后紧接着再跑一遍逐骰循环处理 ``r`` / ``ro`` / ``R`` / ``a``，同样按源码
   顺序；其它记号在此阶段忽略。
2. **全局、先处理 ``k``**：把所有修饰符里出现的 ``k`` 依次前移处理（每个 ``k``
   对当前整体结果降序取前 n 个）。
3. **全局、再按源码顺序处理其余** ``K`` / ``kh`` / ``kl`` / ``dh`` / ``dl`` /
   ``u`` / ``s`` / ``c``。
4. **收尾**：``collection_items`` 上限检查。

由此可推出几条容易被写错的语义：

* ``1d1!``：初值 1 等于面数 1，循环永不停止，直到预算耗尽，报
  ``limit.generated_values``（语料 ``explode_budget``）；**不会**得到
  ``total = 1``。``1d1e`` 同理（``explode_alias_budget``）。
* ``1d1R1``：``R`` 在 ``current <= 1`` 时不断重掷，同样只能靠预算终止
  （``reroll_until_budget``）。
* ``1d1r1`` / ``1d1ro1``：只重掷一次，因此正常返回 ``total = 1``；但重掷会多消耗
  一个生成值；``src/calculator.rs`` 的单元测试
  ``every_reroll_variant_consumes_the_configured_budget`` 用 ``roll_limit = 1``
  固定了「重掷也计预算」这一点（该单元测试在 ``src/calculator.rs``，不在
  conformance 语料里）。
* 每次修饰符处理都会按当前骰值个数计 ``work_units``（``charge_modifier_work``），
  所以长链修饰符也会消耗预算。

4.4 修饰符语义（与 3.4 同序）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

本表与 3.4 是同一集合、同一顺序（15 行），不引入第二套别名表。所有语义已实现。

.. list-table::
   :header-rows: 1
   :widths: 10 58 32

   * - 记号
     - 语义（逐骰 / 全局）
     - 示例
   * - ``!``
     - 逐骰：值 == 面数时继续掷并追加，直到不等；无次数上限
     - ``1d1!`` → ``limit.generated_values``
   * - ``e``
     - 同 ``!``（独立 AST 变体 ``ExplodeAlias``）
     - ``1d1e`` → ``limit.generated_values``
   * - ``K n``
     - 全局：降序取前 n 个。源码注释称「explode then keep high」，但**没有**
       explode 步骤，属已知缺陷（#24）
     - ``2d1K1`` → ``total = 1``（语料 ``keep_and_explode_incomplete``）
   * - ``r n``
     - 逐骰：若该骰任一值 ``<= n``，重掷一次并用**单个**新值替换该骰全部结果
     - ``1d1r1`` → ``total = 1``
   * - ``ro n``
     - 逐骰：只重掷第一个 ``<= n`` 的位置，其余保留
     - ``1d6ro1`` → ``total`` ∈ ``1..=6``（重掷后可能仍是 1）
   * - ``R n``
     - 逐骰：当最后一个值 ``<= n`` 时继续重掷，最终只保留一个值；可能永不终止，
       靠预算兜底
     - ``1d1R1`` → ``limit.generated_values``
   * - ``a n``
     - 逐骰：若任一值 ``<= n``，重掷一次并把该骰所有值求和，结果为一个值
     - ``1d1a1`` → ``total = 2``
   * - ``k n``
     - 全局：降序取前 n 个（即 keep high），先于其它全局修饰符执行
     - ``2d1k1`` → ``total = 1``
   * - ``kh n``
     - 全局：保留高 n 个
     - ``2d1kh1`` → ``total = 1``
   * - ``kl n``
     - 全局：保留低 n 个
     - ``2d1kl1`` → ``total = 1``
   * - ``dh n``
     - 全局：弃掉高 n 个
     - ``2d1dh1`` → ``total = 1``
   * - ``dl n``
     - 全局：弃掉低 n 个
     - ``2d1dl1`` → ``total = 1``
   * - ``u``
     - 全局：按出现顺序去重
     - ``2d1u`` → ``total = 1``
   * - ``s``
     - 全局：升序排序，值全保留，``total`` 不变
     - ``2d1s`` → ``total = 2``，``flattened_rolls = 2``
   * - ``c n``
     - 全局：统计值**等于 n** 的个数，结果是一个值（不是「取前 n 个」）
     - ``2d1c1`` → ``total = 2``；``3d1kh2c1`` → ``total = 2``

``flattened_rolls`` 反映修饰符后的骰值个数：``k``/``kh``/``c`` 会收缩，
``s``/``u`` 保留多值，``r``/``a``/``R`` 把一颗骰压成一个值。

4.5 ``2.0`` 语义（未实现）
~~~~~~~~~~~~~~~~~~~~~~~~~~~

按 RFC-0001，以下语义在代码中尚不可用：

* **类型化值**：``Scalar`` / ``Values`` / ``Text`` / ``Boolean`` / 嵌套集合；
  算术只接受 scalar 兼容值并返回 ``Scalar``。未实现（#39）。
* **不可变变量**：``${name}`` 由宿主在执行请求里提供，程序内不可赋值；条件块内
  ``${0}`` 遮蔽同名实参。未实现（#39）。
* **数值区间与加权列表骰**：``2d[1..6]``、``2l["a"[3],"b"[1]]``；权重只用整数或
  百分比，抽样全程用归一化整数，不用浮点；相同的文本项先合并权重。未实现
  （#40）。
* **validator 选项**：``f`` / ``c`` / ``r`` / ``R`` / ``a`` / ``e`` 的参数是
  ``scoped_validator``，见 5.3。未实现（#41）。
* **合并 / 绑定 / 出现次数 / 涂色 / 拆分 / 分组**：``m(expr)``、``b``、``o(n)``、
  ``p[name:n]``、``y``、``g n``。未实现（#42）。
* **repeat 与条件块**：``repeat(expr; instr; …)`` 有预算上界；
  ``i[validator]{…}{…}`` 按条件选择分支。未实现（#43）。
* **多指令 Program 与共享预算**：``;`` 分隔，一条指令失败即整体失败。未实现
  （#38）。

5. 优先级表
-----------

5.1 ``1.x``（已实现：单层、左结合）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 20 16 54

   * - 层级或构造
     - 运算符
     - 结合性
     - 说明
   * - 1（唯一算术层）
     - ``+ - * / ^``
     - 全部左结合
     - 同层，按书写顺序从左到右折叠；括号是唯一能改变求值顺序的手段
   * - 括号
     - ``( )``
     - 不适用
     - 仅分组，产生 ``Paren`` 节点，不参与优先级比较

对照示例：``1 + 2 * 3 = 9``、``2 ^ 3 ^ 2 = 64``、``1d1 + 2 * 3 = 9``。其中后两条
由语料 ``left_associative_power`` 与 ``flat_operator_precedence`` 直接固定；
``1 + 2 * 3`` 与前者同构，按同一左折叠规则得 ``9``。``^`` 是幂；``**`` 在 ``1.x`` 里不是运算符，``2 ** 3`` 报
``parse.invalid_syntax``。

5.2 ``2.0``（未实现，issue #16）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 24 18 48

   * - 层级
     - 运算符
     - 结合性
     - 状态
   * - 1（最强）
     - 括号 / primary pipeline
     - —
     - 未实现（#16）
   * - 2
     - ``**``
     - 右结合
     - 未实现（#16）
   * - 3
     - 前缀 ``+`` ``-``
     - —（前缀，不涉结合性）
     - 未实现（#16）
   * - 4
     - ``*`` ``/``
     - 左结合
     - 未实现（#16）
   * - 5（最弱）
     - ``+`` ``-``
     - 左结合
     - 未实现（#16）

这是一次不兼容变更：``1 + 2 * 3`` 在 ``1.x`` 为 ``9``，在 ``2.0`` 分层下为
``7``。迁移提示由 issue #29 负责；在 #16 落地前，本文的规范性结论以 5.1 为准。

5.3 ``2.0`` validator 的逻辑算子（未实现，issue #41）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 12 26 62

   * - 算子
     - 含义
     - 说明
   * - ``&``
     - 逻辑与（and）
     - ``validator_list`` 内连接两个 predicate
   * - ``^``
     - 逻辑异或（xor）
     - 与 ``1.x`` 的 ``^``（幂运算）**无关**，只出现在 validator 内
   * - ``|``
     - 逻辑或（or）
     - 同上，仅在 ``[...]`` 内有效

配套产生式（RFC-0001）：

.. code-block:: text

   scoped_validator = { compare_scope? ~ validator_list }
   validator_list   = { "[" ~ predicate ~ (logic_operator ~ predicate)* ~ "]" }
   compare_scope    = { "*" | ":" | "." }
   logic_operator   = { "&" | "^" | "|" }
   predicate        = _{ modulo_predicate | range_predicate | comparison }
   range_predicate  = { range_bounds }
   modulo_predicate = { "%" ~ scalar_operand ~ comparison }
   comparison       = { compare_operator? ~ operand }
   compare_operator = { ">=" | "<=" | "!=" | "=" | ">" | "<" }
   operand          = _{ dynamic_variable | signed_number | string | source_bound }
   source_bound     = { ^"min" | ^"max" }

作用域前缀 ``*`` / ``:`` / ``.`` 分别对应整个表达式、当前指令、当前值（RFC-0001
的 scoped validator 章节）；三者语义在 #41 落地时还会细化，本文不展开。

6. 错误码
---------

错误码定义在 ``src/errors.rs``，形态为 ``ErrorEnvelope``（``schema_version =
"2.0"``、``phase``、``code``、``message``、可选 ``replacement``）。错误码用
``[code] message`` 的文本形式出现在 ``message`` 里，语料用
``message_contains`` 断言。

.. list-table::
   :header-rows: 1
   :widths: 28 10 44 18

   * - 错误码
     - phase
     - 触发条件
     - 语料 / 备注
   * - ``parse.invalid_syntax``
     - Parse
     - 输入不匹配文法：空串、尾部残留、未闭合括号、未知修饰符
     - ``empty_program``、``trailing_operator``、``unclosed_parenthesis``、
       ``unknown_modifier``
   * - ``parse.invalid_syntax``
     - Parse
     - ``roll`` 收到多条指令
     - ``multiple_instructions_in_roll``（消息「只接受一条指令」）
   * - ``validate.invalid_expression``
     - Validate
     - 骰子数量或面数 ``<= 0``
     - ``zero_dice_count``、``zero_dice_sides``
   * - ``arithmetic.overflow``
     - Evaluate
     - ``checked_add/sub/mul/div/pow`` 或聚合求和溢出
     - ``addition_overflow``、``division_overflow``、``exponentiation_overflow``
   * - ``arithmetic.divide_by_zero``
     - Evaluate
     - 除数为 0
     - ``division_by_zero``
   * - ``arithmetic.invalid_exponent``
     - Evaluate
     - 指数为负或不落在 ``u32`` 内
     - ``negative_exponent``、``exponent_above_u32``
   * - ``random.invalid_seed``
     - Validate
     - 种子格式非法
     - 见 ``randomness`` 文档
   * - ``random.entropy_unavailable``
     - Evaluate
     - 请求系统熵源失败
     - 平台相关
   * - ``limit.generated_values``
     - Evaluate
     - 生成骰值数超过上限（默认 10000）
     - ``explode_budget``、``reroll_until_budget``、``program_shared_roll_budget``
   * - ``limit.collection_items``
     - Evaluate
     - 单次骰子收集的骰值个数超限
     - ``resource.rs`` 的 ``RESOURCE_LIMITS``
   * - ``limit.work_units``
     - Evaluate
     - 修饰符处理与求值的工作量超限
     - 每轮修饰符按骰值个数计费
   * - ``limit.parsed_instructions``
     - Parse
     - 解析出的指令条数超限
     - ``2.0`` 多指令相关（#38）
   * - ``policy.invalid_limit``
     - 构造期
     - 自定义 policy 的某项上限非法
     - 非语料覆盖
   * - ``policy.limit_above_hard_max``
     - 构造期
     - 传入的上限超过硬上限
     - 非语料覆盖
   * - ``evaluate.internal``
     - Evaluate
     - 内部不一致（不应发生的状态）
     - 兜底

具体的默认值与硬上限见 ``src/resource.rs`` 的 ``RESOURCE_LIMITS`` 与
:doc:`limits`。

7. 示例与期望结果
-----------------

「依据」列写语料 ``id``；标「推导」的示例由 3.3/4.3/4.4 的规则直接得出，本次
未在沙箱内实跑（见 9）。

.. list-table::
   :header-rows: 1
   :widths: 16 44 40

   * - 表达式
     - 期望
     - 依据
   * - ``7``
     - ``total = 7``，``flattened_rolls = 0``
     - ``integer_literal``
   * - ``-2``
     - ``total = -2``
     - ``negative_integer_literal``
   * - ``3d1``
     - ``total = 3``，``flattened_rolls = 3``
     - ``deterministic_dice``
   * - ``  1d1  ``
     - ``total = 1``（首尾空白忽略）
     - ``surrounding_whitespace``
   * - ``5 / 2``
     - ``total = 2``（向零截断）
     - ``integer_division``
   * - ``1 + 2 * 3``
     - ``total = 9``（``1.x`` 同层左结合）
     - ``flat_operator_precedence`` 同型；``2.0`` 分层下应为 7，未实现（#16）
   * - ``1d1 + 2 * 3``
     - ``total = 9``，``flattened_rolls = 1``
     - ``flat_operator_precedence``
   * - ``(1 + 2) * 3``
     - ``total = 9``
     - ``parenthesized_expression``
   * - ``2 ^ 3 ^ 2``
     - ``total = 64``（左结合）
     - ``left_associative_power``
   * - ``-2 ^ 2``
     - ``total = 4``（负号属于 ``number``）
     - 推导
   * - ``1d1!``
     - ``limit.generated_values``（预算 10000 耗尽，不是 ``total = 1``）
     - ``explode_budget``
   * - ``1d1e``
     - ``limit.generated_values``
     - ``explode_alias_budget``
   * - ``1d1R1``
     - ``limit.generated_values``
     - ``reroll_until_budget``
   * - ``1d1r1``
     - ``total = 1``（重掷一次；多消耗一个生成值）
     - ``reroll``
   * - ``1d1ro1``
     - ``total = 1``
     - ``reroll_once``
   * - ``1d6ro1``
     - ``total`` ∈ ``1..=6``：重掷后仍可能掷出 1
     - 推导
   * - ``1d1a1``
     - ``total = 2``（1 + 新掷的 1）
     - ``reroll_and_add``
   * - ``2d1K1``
     - ``total = 1``（只 keep high，未 explode）
     - ``keep_and_explode_incomplete``
   * - ``2d1c1``
     - ``total = 2``（统计等于 1 的个数）
     - ``count``
   * - ``3d1kh2c1``
     - ``total = 2``
     - ``modifier_composition_order``
   * - ``2d1s``
     - ``total = 2``，``flattened_rolls = 2``
     - ``sort``
   * - ``1 # attack``
     - ``total = 1``，``comment = "attack"``
     - ``trailing_comment``
   * - ``1 / 0``
     - ``arithmetic.divide_by_zero``
     - ``division_by_zero``
   * - ``2 ^ -1``
     - ``arithmetic.invalid_exponent``
     - ``negative_exponent``
   * - ``2 ** 3``
     - ``parse.invalid_syntax``（``**`` 不是 ``1.x`` 运算符）
     - 推导
   * - ``1d1z``
     - ``parse.invalid_syntax``（未知修饰符）
     - ``unknown_modifier``
   * - ``1; 2``
     - ``parse.invalid_syntax``，消息含「只接受一条指令」
     - ``multiple_instructions_in_roll``
   * - ``0d6`` / ``1d0``
     - ``validate.invalid_expression``
     - ``zero_dice_count`` / ``zero_dice_sides``

8. 与 issue 的状态映射
----------------------

.. list-table::
   :header-rows: 1
   :widths: 10 40 14 30

   * - issue
     - 内容
     - 状态
     - 本文对应
   * - #7
     - RFC-0001：v2 语言设计（已关闭，设计已接纳）
     - 已关闭
     - 3.5、4.5、5.2
   * - #16
     - v2 Pratt 优先级与规范表达式
     - open
     - 3.2、5.2
   * - #15
     - v2 keep / filter / sort / count / unique
     - open
     - 3.4、4.4、4.5
   * - #24
     - 有界 explode / reroll / keep-and-explode
     - open
     - 3.4、4.3、4.4（``K`` 缺陷）
   * - #26
     - Python 领域异常层次
     - open
     - 4.2
   * - #29
     - v1→v2 兼容诊断与迁移指南
     - open
     - 3.2、5.2
   * - #37
     - v2.0 RC→GA 发布清单
     - open
     - 全文（未实现项总账）
   * - #38
     - 多指令 Program
     - open
     - 3.1、4.5
   * - #39
     - 类型化值、闭区间、不可变变量
     - open
     - 2.2、3.5、4.5
   * - #40
     - 数值区间骰与加权列表骰
     - open
     - 2.2、3.5、4.5
   * - #41
     - 作用域 validator 求值
     - open
     - 3.5、5.3
   * - #42
     - merge / bind / occurrences / paint / split / group
     - open
     - 3.5、4.5
   * - #43
     - repeat 与条件块
     - open
     - 3.5、4.5
   * - #51
     - v2 表面语法是否按非代码宿主与 LLM 工具调用重议
     - open
     - 2.2、3.3（兼容写法）
   * - #3
     - Program 采样与精确概率分析边界
     - open
     - 9（待拍板）

9. 待拍板与 TODO
----------------

1. **精确概率分析的边界（issue #3）。** ``!`` / ``R`` 这类无界循环只能靠预算
   终止，因此「哪些表达式可以给出精确分布」需要与 #3 一起定义：目前只能确定
   有界表达式（不含 ``!``、``e``、``R``）可枚举。本文不预设结论。
2. **v2 表面语法是否按 issue #51 重议。** 本文的 ``2.0`` 产生式一律以
   ``docs/rfcs/0001-v2-target.pest`` 为准。若 #51 决定调整（例如保留 ``1.x``
   的 ``!``、``ro`` 写法，或改变 ``WHITESPACE`` 对 ``\r`` 的处理），3.3、3.5
   与 4.5 需同步更新；本文不先于讨论下结论。
3. **``values_list`` 的 issue 归属**：现有 issue 中没有独立条目，暂标 ``TODO``。
4. **空白宽容度**（骰子记号内部是否接受空白）目前没有 conformance 用例固定，
   本文只在 3.3 写了词法层面的规则，不给具体写法的等价结论；建议 CI 补一条
   显式用例后再写进示例表。
5. **``k`` 与 ``K`` 是否应有区别**：当前实现里两者都是「降序取前 n 个」，
   ``K`` 缺 explode 步骤（#24）。语料以 ``known_defect`` 标记，规范是否把它写成
   正式语义（而不是缺陷）需维护者拍板。
6. **``a``（reroll-and-add）的逐骰语义**：实现是「任一值 ``<= n`` 时该骰压成
   一个和」。若设计意图是「逐值重掷」，需在 #24 里澄清。
7. **``2.0`` 的 ``\r``**：目标文法把 ``WHITESPACE`` 收紧为空格/制表/``NEWLINE``，
   与 ``1.x`` 不同；属于 #51 的兼容性议题。

细节讨论建议开一个 tracking issue（标题如「expression spec: tracking follow-ups」），
本 PR 随讨论同步更新；本文的 ``TODO`` 项在对应 issue 关闭时一并消解。
