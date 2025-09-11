use std::env;
use std::fs::File;
use std::io::Write;
use std::path::Path;

fn main() {
    let out_dir = env::var("OUT_DIR").unwrap();
    let dest_path = Path::new(&out_dir).join("oneroll_grammar.rs");
    let mut f = File::create(&dest_path).unwrap();

    f.write_all(b"use pest_derive::Parser;\n").unwrap();
    f.write_all(b"\n").unwrap();
    f.write_all(b"#[derive(Parser)]\n").unwrap();
    f.write_all(b"#[grammar = \"src/oneroll/grammar.pest\"]\n").unwrap();
    f.write_all(b"pub struct Grammar;\n").unwrap();
}
