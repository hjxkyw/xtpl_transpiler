# xtpl Transpiler

> **WARNING:**
> This code is experimental and provided for educational purposes only. 
> Use at your own risk. The author assumes no responsibility or liability 
> for any bugs, data loss, or production issues resulting from its use.
> 
> *Note: This is not a true compiler; it is a text transformation tool powered entirely by regular expressions.*

`xtpl` is an extension language for **ADVPL / TLPP** that brings modern functional programming paradigms, safety features, and cleaner syntax sugars (such as block-scoped variables, pipelines, pattern matching, and RAII-style resource cleanup) to the Totvs Protheus ecosystem. 

This repository contains the official Python-based transpiler that translates `xtpl` source code into standard, compliant ADVPL/TLPP code.

---

## Features

* **Block-Scoped Variables (`let`) & Hoisting**: Strict local variable declarations with automated name-mangling to eliminate variable collision risks.
* **Conditional Assignment (`?=`)**: Assigns a default value to a variable only if it currently evaluates to `Nil`.
* **Resource Deferral (`defer`)**: Ensures clean resource teardown (like closing files or cursors) automatically when a function exits, similar to RAII.
* **Monadic Binding (`with` / `without`)**: Null-safe execution blocks with mandatory fallback clauses.
* **Structural Pattern Matching (`given` / `when`)**: Switch/case alternative with support for custom evaluators (`EQ`, `GTR`, inline functions).
* **Implicit Arrays (`gather` / `take`)**: Syntactic sugar for dynamically building arrays.
* **Pipeline Operator (`==>`)**: Functional data flow that passes expressions directly into downstream functions or collection macros.
* **Functional Collections**: Native macros for `map`, `filter`, `reject`, `reduce`, `zip`, `take`, `drop`, `chunks`, `slide`, `distinct`, `reverse`, `flatten`, and `enumerate`.
* **Safety Operators**: Optional chaining (`?.`), Elvis operator (`?:`), and safe pipelines (`?=>`).
* **Postfix Modifiers**: Concise conditional execution like `return x if cond` or `exec body if cond`.

---

## Installation & Requirements

* Python 3.x

Clone the repository and ensure you have the script ready:

git clone https://github.com/your-username/xtpl-transpiler.git
cd xtpl-transpiler

---

## Usage

Run the transpiler from the command line by passing your `xtpl` input file and your target ADVPL output file:

python xtpl_transpiler.py <input.xtpl> <output.prg>

### Example

If you have an `xtpl` file utilizing features like `defer` and conditional assignment:

User Function ProcessData()
  let fileHandle ?= FOpen("data.txt")
  defer FClose(fileHandle)
  
  if fileHandle == -1
    return .F. if lSilent
    ConOut("Error opening file")
    return .F.
  EndIf
  
  // Processing logic...
  Return .T.

The transpiler will output valid ADVPL/TLPP code complete with automated variable hoisting, scope-mangling, and safety injections.

---

## License

Distributed under the MIT License. See `LICENSE` for more information.
