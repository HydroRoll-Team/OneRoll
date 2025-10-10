OneRoll
=======

.. toctree::
   :maxdepth: 2
   :caption: Contents


====

 - Basic dice rolling (XdY)
 - Mathematical operations: +, -, *, /, ^
 - Modifiers: !, kh, kl, dh, dl, r, ro
 - Bracket support
 - User comments (e.g., 3d6 + 2 # Attack roll)
 - Complete error 
 - Statistical rolling and analysis
 - Rich terminal UI (TUI) via textual
 - Python SDK and CLI


.. code-block:: peg
   :caption: Dice Expression Grammar

   WHITESPACE = _{ " " | "\t" | "\n" | "\r" }
   number = @{ "-"? ~ ("0" | ('1'..'9' ~ ('0'..'9')*)) }
   comment = { "#" ~ (!"\n" ~ ANY)* }
   dice_expr = { dice_term ~ (op ~ dice_term)* ~ comment? }
   dice_term = { 
      dice_roll 
      | paren_expr 
      | number 
   }
   paren_expr = { "(" ~ dice_expr ~ ")" }
   dice_roll = { 
      number ~ "d" ~ dice_sides ~ modifiers?
   }
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
   explode = { "!" }
   explode_alias = { "e" }
   explode_keep_high = { "K" ~ number }
   reroll = { "r" ~ number }
   reroll_once = { "ro" ~ number }
   reroll_until = { "R" ~ number }
   reroll_add = { "a" ~ number }
   keep_alias = { "k" ~ number }
   keep_high = { "kh" ~ number }
   keep_low = { "kl" ~ number }
   drop_high = { "dh" ~ number }
   drop_low = { "dl" ~ number }
   unique = { "u" }
   sort = { "s" }
   count = { "c" ~ number }
   op = { "+" | "-" | "*" | "/" | "^" }
   main = { SOI ~ dice_expr ~ EOI }

