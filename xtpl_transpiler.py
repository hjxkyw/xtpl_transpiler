#!/usr/bin/env python3
# --------------------------------------------------------------------------------
# xtpl_transpiler.py
# --------------------------------------------------------------------------------

import sys
import re

def transpile(source_code):
  lines = source_code.splitlines()
  out_lines = []
  
  in_function = False
  function_buffer = []
  hoisted_vars = set()
  defer_stack = []
  
  scope_stack = [0]
  scope_counter = 0
  scope_vars = { 0: set() }
  scope_var_mangling = { 0: {} }
  
  reserved_words = {
    "function", "static", "user", "return", "if", "else", "elseif", "endif",
    "for", "next", "while", "enddo", "do", "local", "private", "public",
    "with", "without", "orwith", "given", "when", "otherwise", "end", "let",
    "conout", "len", "eval", "array", "aadd", "substr", "userexception"
  }
  
  re_func = re.compile(r'^\s*(?:User\s+|Static\s+)?(?:Function|Method)\b', re.IGNORECASE)
  re_scope_in = re.compile(r'^\s*(?:IF|FOR|WHILE|BEGIN\s+SCOPE)\b', re.IGNORECASE)
  re_scope_out = re.compile(r'^\s*(?:ENDIF|NEXT|ENDDO|END\s+SCOPE)\b', re.IGNORECASE)
  
  re_let = re.compile(r'^\s*LET\s+([a-zA-Z0-9_]+)\s*:=\s*', re.IGNORECASE)
  re_let_defined_or = re.compile(r'^\s*LET\s+([a-zA-Z0-9_]+)\s*\?=\s*(.+)$', re.IGNORECASE)
  re_defined_or = re.compile(r'^\s*([a-zA-Z0-9_]+)\s*\?=\s*(.+)$', re.IGNORECASE)
  
  re_assign = re.compile(r'^\s*([a-zA-Z0-9_]+)\s*:=\s*', re.IGNORECASE)
  
  re_foreach = re.compile(r'^\s*FOR\s+EACH\s+([a-zA-Z0-9_]+)\s*(?:,\s*([a-zA-Z0-9_]+))?\s+IN\s+(.+)$', re.IGNORECASE)
  re_for = re.compile(r'^\s*FOR\s+([a-zA-Z0-9_]+)\s*:=\s*(.+)$', re.IGNORECASE)
  re_fortimes = re.compile(r'^\s*FOR\s+(.+?)\s+TIMES(?:,\s*([a-zA-Z0-9_]+))?\s*$', re.IGNORECASE)

  re_defer = re.compile(r'^\s*defer\s+(.+)$', re.IGNORECASE)
  re_explicit_return = re.compile(r'^\s*return\b', re.IGNORECASE)
  re_postfix_return = re.compile(r'^\s*return\b(?P<val>.*?)\s+if\s+(?P<cond>.+)$', re.IGNORECASE)
  re_postfix_exec = re.compile(r'^\s*exec\s+(?P<body>.+?)\s+if\s+(?P<cond>.+)$', re.IGNORECASE)
  re_postfix_general = re.compile(r'^\s*(?P<body>.+?)\s+(?P<kw>if|while)\s+(?P<cond>.+)$', re.IGNORECASE)

  re_with_start = re.compile(r'^\s*with\s+(.+?)\s+do\s*$', re.IGNORECASE)
  re_orwith = re.compile(r'^\s*orwith\s+(.+?)\s+do\s*$', re.IGNORECASE)
  re_without_start = re.compile(r'^\s*without\s+(.+?)\s+do\s*$', re.IGNORECASE)
  re_endwith = re.compile(r'^\s*end\s+with\b', re.IGNORECASE)
  re_endwithout = re.compile(r'^\s*end\s+without\b', re.IGNORECASE)

  re_given_start = re.compile(r'^\s*given\s+(.+?)(?:\s+as\s+([a-zA-Z0-9_]+))?\s+do\s*$', re.IGNORECASE)
  re_when_start = re.compile(r'^\s*when\s+(.+?)\s+do\s*$', re.IGNORECASE)
  re_otherwise_start = re.compile(r'^\s*otherwise\s*$', re.IGNORECASE)
  re_endgiven = re.compile(r'^\s*end\s+given\b', re.IGNORECASE)

  # Gather / Take patterns
  re_gather_start = re.compile(r'^\s*(?:let\s+[a-zA-Z0-9_]+\s*:=\s*)?gather\s*$', re.IGNORECASE)
  re_endgather = re.compile(r'^\s*end\s+gather\b', re.IGNORECASE)
  re_take = re.compile(r'\btake\s*\(\s*(.+?)\s*\)', re.IGNORECASE)

  # Smart Print pattern
  re_xtpl_print = re.compile(r'\bxtplPrint\s*\(\s*(.+)\s*\)', re.IGNORECASE)

  re_map_filter_reject_lambda = re.compile(r'\b(map|filter|reject)\s*\(\s*\[\s*([a-zA-Z0-9_]+)\s*\]\s*(.+?)\s*\)', re.IGNORECASE)
  re_reduce_lambda = re.compile(r'\breduce\s*\(\s*\[\s*([a-zA-Z0-9_]+)\s*,\s*([a-zA-Z0-9_]+)\s*\]\s*(.+?)\s*,\s*(.+?)\s*\)', re.IGNORECASE)
  re_meta_reduce = re.compile(r'^\[\s*([\+\-\*\/\bmax\b\bmin\b]+)\s*\]$', re.IGNORECASE)
  
  re_zip_simple = re.compile(r'\bZ\s*\(\s*([^,\)]+)\s*\)', re.IGNORECASE)
  re_zip_combiner = re.compile(r'\bZ\s*\(\s*([^,]+)\s*,\s*\[\s*([a-zA-Z0-9_]+)\s*,\s*([a-zA-Z0-9_]+)\s*\]\s*(.+?)\s*\)', re.IGNORECASE)
  
  re_take_drop = re.compile(r'\b(take|drop)\s*\(\s*(.+?)\s*\)', re.IGNORECASE)
  re_chunks_slide = re.compile(r'\b(chunks|slide)\s*\(\s*(.+?)\s*\)', re.IGNORECASE)
  re_distinct_reverse_flatten = re.compile(r'^\s*(distinct|reverse|flatten|enumerate)\s*$', re.IGNORECASE)
  
  re_elvis = re.compile(r'(.+?)\s*\?:\s*(.+)', re.IGNORECASE)
  re_optional_chain = re.compile(r'\b([a-zA-Z0-9_]+)\s*\?\.\s*([a-zA-Z0-9_]+)(?:\s*\?\.\s*([a-zA-Z0-9_]+))?', re.IGNORECASE)
  re_safe_pipeline = re.compile(r'(.+?)\s+fallback\s+(.+)$', re.IGNORECASE)

  def register_variable(var_name, curr_scope):
    v_lower = var_name.lower()
    if v_lower in reserved_words:
      raise SyntaxError(f"Cannot use reserved word '{var_name}' as a variable name.")
    if v_lower not in scope_vars[curr_scope]:
      mangled = f"__blk_{curr_scope}_{var_name}"
      scope_vars[curr_scope].add(v_lower)
      scope_var_mangling[curr_scope][v_lower] = mangled
      hoisted_vars.add(mangled)
      return mangled
    return scope_var_mangling[curr_scope][v_lower]

  def flush_function(line_num):
    if not function_buffer:
      return
    out_lines.append(function_buffer[0])
    if hoisted_vars:
      for var in sorted(hoisted_vars):
        out_lines.append(f"  Local {var}")
    
    body_lines = function_buffer[1:]
    for line in body_lines:
      out_lines.append(line)
      
    function_buffer.clear()
    hoisted_vars.clear()
    defer_stack.clear()

  with_stack = []
  gather_stack = []
  temp_var_counter = 0

  def parse_when_condition(target, cond):
    cond = cond.strip()
    cond_upper = cond.upper()
    if cond_upper.startswith("EQ(") and cond.endswith(")"):
      return f"{target} == {cond[3:-1]}"
    elif cond_upper.startswith("NEQ("):
      return f"{target} != {cond[4:-1]}"
    elif cond_upper.startswith("GTR("):
      return f"{target} > {cond[4:-1]}"
    elif cond_upper.startswith("LT("):
      return f"{target} < {cond[3:-1]}"
    elif cond_upper.startswith("GEQ("):
      return f"{target} >= {cond[4:-1]}"
    elif cond_upper.startswith("LTE("):
      return f"{target} <= {cond[3:-1]}"
    elif "(" in cond and cond.endswith(")"):
      paren_idx = cond.index("(")
      func_name = cond[:paren_idx]
      args = cond[paren_idx+1:-1].strip()
      return f"{func_name}({target}, {args})" if args else f"{func_name}({target})"
    elif any(cond.startswith(op) for op in ['>', '<', '=', '!', 'in']):
      return f"{target} {cond}"
    else:
      return f"{target} == {cond}"

  def transpile_feed_chains(line, curr_scope, line_idx):
    nonlocal temp_var_counter

    if "==>" not in line:
      return line
      
    parts = [p.strip() for p in line.split("==>")]
    if not parts:
      return line
      
    current_expr = parts[0]
    additional_statements = []
    
    for next_func in parts[1:]:
      next_func = next_func.strip()
      lambda_match = re_map_filter_reject_lambda.search(next_func)
      reduce_match = re_reduce_lambda.search(next_func)
      meta_reduce_match = re_meta_reduce.search(next_func)
      zip_combiner_match = re_zip_combiner.search(next_func)
      zip_simple_match = re_zip_simple.search(next_func)
      take_drop_match = re_take_drop.search(next_func)
      chunks_slide_match = re_chunks_slide.search(next_func)
      drf_match = re_distinct_reverse_flatten.search(next_func)
      
      if lambda_match:
        op_type = lambda_match.group(1).lower()
        alias_user = lambda_match.group(2).strip()
        block_body = lambda_match.group(3).strip()
        
        mangled_alias = register_variable(alias_user, curr_scope)
        body_transpiled = re.sub(rf'\b{alias_user}\b', mangled_alias, block_body, flags=re.IGNORECASE)
        
        temp_pipe = f"__pipe_tmp_{curr_scope}_{temp_var_counter}"
        temp_var_counter += 1
        hoisted_vars.add(temp_pipe)
        
        if op_type == "filter":
          func_name = "__xtpl_filter"
        elif op_type == "reject":
          func_name = "__xtpl_reject"
        else:
          func_name = "__xtpl_map"
          
        additional_statements.append(f"{temp_pipe} := {func_name}({current_expr}, {{|{mangled_alias}| {body_transpiled}}})")
        current_expr = temp_pipe
      elif reduce_match:
        acc_user = reduce_match.group(1).strip()
        item_user = reduce_match.group(2).strip()
        block_body = reduce_match.group(3).strip()
        init_val = reduce_match.group(4).strip()
        
        mangled_acc = register_variable(acc_user, curr_scope)
        mangled_item = register_variable(item_user, curr_scope)
        
        body_transpiled = re.sub(rf'\b{acc_user}\b', mangled_acc, block_body, flags=re.IGNORECASE)
        body_transpiled = re.sub(rf'\b{item_user}\b', mangled_item, body_transpiled, flags=re.IGNORECASE)
        
        temp_pipe = f"__pipe_tmp_{curr_scope}_{temp_var_counter}"
        temp_var_counter += 1
        hoisted_vars.add(temp_pipe)
        
        additional_statements.append(
          f"{temp_pipe} := __xtpl_reduce({current_expr}, {{|{mangled_acc}, {mangled_item}| {body_transpiled}}}, {init_val})"
        )
        current_expr = temp_pipe
      elif meta_reduce_match:
        op = meta_reduce_match.group(1).strip()
        if op == "+":
          init_val = "0"
          expr_block = "acc + item"
        elif op == "*":
          init_val = "1"
          expr_block = "acc * item"
        elif op.lower() == "max":
          init_val = f"{current_expr}[1]"
          expr_block = "Max(acc, item)"
        elif op.lower() == "min":
          init_val = f"{current_expr}[1]"
          expr_block = "Min(acc, item)"
        else:
          raise SyntaxError(f"Line {line_idx+1}: Unsupported reduction meta-operator '[{op}]'")
          
        temp_pipe = f"__pipe_tmp_{curr_scope}_{temp_var_counter}"
        temp_var_counter += 1
        hoisted_vars.add(temp_pipe)
        
        additional_statements.append(
          f"{temp_pipe} := __xtpl_reduce({current_expr}, {{|acc, item| {expr_block}}}, {init_val})"
        )
        current_expr = temp_pipe
      elif zip_combiner_match:
        other_arr = zip_combiner_match.group(1).strip()
        left_user = zip_combiner_match.group(2).strip()
        right_user = zip_combiner_match.group(3).strip()
        block_body = zip_combiner_match.group(4).strip()
        
        mangled_left = register_variable(left_user, curr_scope)
        mangled_right = register_variable(right_user, curr_scope)
        
        body_transpiled = re.sub(rf'\b{left_user}\b', mangled_left, block_body, flags=re.IGNORECASE)
        body_transpiled = re.sub(rf'\b{right_user}\b', mangled_right, body_transpiled, flags=re.IGNORECASE)
        
        temp_pipe = f"__pipe_tmp_{curr_scope}_{temp_var_counter}"
        temp_var_counter += 1
        hoisted_vars.add(temp_pipe)
        
        additional_statements.append(
          f"{temp_pipe} := __xtpl_zip({current_expr}, {other_arr}, {{|{mangled_left}, {mangled_right}| {body_transpiled}}})"
        )
        current_expr = temp_pipe
      elif zip_simple_match:
        other_arr = zip_simple_match.group(1).strip()
        
        temp_pipe = f"__pipe_tmp_{curr_scope}_{temp_var_counter}"
        temp_var_counter += 1
        hoisted_vars.add(temp_pipe)
        
        additional_statements.append(
          f"{temp_pipe} := __xtpl_zip({current_expr}, {other_arr}, Nil)"
        )
        current_expr = temp_pipe
      elif take_drop_match:
        op_type = take_drop_match.group(1).lower()
        count_expr = take_drop_match.group(2).strip()
        
        temp_pipe = f"__pipe_tmp_{curr_scope}_{temp_var_counter}"
        temp_var_counter += 1
        hoisted_vars.add(temp_pipe)
        
        func_name = "__xtpl_take" if op_type == "take" else "__xtpl_drop"
        additional_statements.append(f"{temp_pipe} := {func_name}({current_expr}, {count_expr})")
        current_expr = temp_pipe
      elif chunks_slide_match:
        op_type = chunks_slide_match.group(1).lower()
        size_expr = chunks_slide_match.group(2).strip()
        
        temp_pipe = f"__pipe_tmp_{curr_scope}_{temp_var_counter}"
        temp_var_counter += 1
        hoisted_vars.add(temp_pipe)
        
        func_name = "__xtpl_chunks" if op_type == "chunks" else "__xtpl_slide"
        additional_statements.append(f"{temp_pipe} := {func_name}({current_expr}, {size_expr})")
        current_expr = temp_pipe
      elif drf_match:
        op_type = drf_match.group(1).lower()
        
        temp_pipe = f"__pipe_tmp_{curr_scope}_{temp_var_counter}"
        temp_var_counter += 1
        hoisted_vars.add(temp_pipe)
        
        if op_type == "distinct":
          func_name = "__xtpl_distinct"
        elif op_type == "reverse":
          func_name = "__xtpl_reverse"
        elif op_type == "flatten":
          func_name = "__xtpl_flatten"
        else:
          func_name = "__xtpl_enumerate"
          
        additional_statements.append(f"{temp_pipe} := {func_name}({current_expr})")
        current_expr = temp_pipe
      else:
        if "(" in next_func and next_func.endswith(")"):
          paren_idx = next_func.index("(")
          func_name = next_func[:paren_idx]
          args = next_func[paren_idx+1:-1].strip()
          current_expr = f"{func_name}({current_expr}, {args})" if args else f"{func_name}({current_expr})"
        else:
          current_expr = f"{next_func}({current_expr})"
          
    if additional_statements:
      return "\n  ".join(additional_statements + [current_expr])
    else:
      return current_expr

  def transpile_optional_chaining(line):
    elvis_match = re_elvis.search(line)
    if elvis_match:
      left = elvis_match.group(1).strip()
      right = elvis_match.group(2).strip()
      line = f"If({left} != Nil, {left}, {right})"

    def replace_optional(match):
      obj = match.group(1)
      prop1 = match.group(2)
      prop2 = match.group(3)
      if prop2:
        return f"If({obj} != Nil .And. {obj}:{prop1} != Nil, {obj}:{prop1}:{prop2}, Nil)"
      else:
        return f"If({obj} != Nil, {obj}:{prop1}, Nil)"

    return re_optional_chain.sub(replace_optional, line)

  def transpile_safe_pipelines(line):
    fallback_match = re_safe_pipeline.search(line)
    if fallback_match:
      pipe_expr = fallback_match.group(1).strip()
      fallback_val = fallback_match.group(2).strip()
      if "?=>" in pipe_expr:
        steps = [s.strip() for s in pipe_expr.split("?=>")]
        current = steps[0]
        for step in steps[1:]:
          if "(" in step and step.endswith(")"):
            p_idx = step.index("(")
            fname = step[:p_idx]
            fargs = step[p_idx+1:-1].strip()
            current = f"{fname}({current}, {fargs})" if fargs else f"{fname}({current})"
          else:
            current = f"{step}({current})"
        pipe_expr = current
      return f"__xtpl_safe_pipe({{|| {pipe_expr}}}, {fallback_val})"
    return line

  def transpile_xtpl_print(line):
    print_match = re_xtpl_print.search(line)
    if print_match:
      args_str = print_match.group(1).strip()
      return f"__xtpl_print({{{args_str}}})"
    return line

  for idx, line in enumerate(lines):
    if re_func.search(line):
      flush_function(idx)
      in_function = True
      scope_stack = [0]
      scope_counter = 0
      scope_vars = { 0: set() }
      scope_var_mangling = { 0: {} }
      with_stack.clear()
      gather_stack.clear()
      defer_stack.clear()
      temp_var_counter = 0
      function_buffer.append(line)
      continue
      
    if not in_function:
      out_lines.append(line)
      continue
      
    curr_scope = scope_stack[-1]
    
    stripped = line.strip()
    
    defer_match = re_defer.search(line)
    if defer_match:
      defer_stack.append(defer_match.group(1).strip())
      continue

    if re_gather_start.match(line):
      acc_var = f"__gather_acc_{curr_scope}_{temp_var_counter}"
      temp_var_counter += 1
      hoisted_vars.add(acc_var)
      gather_stack.append(acc_var)
      function_buffer.append(f"{acc_var} := {{}}")
      continue

    if re_endgather.match(line) and gather_stack:
      acc_var = gather_stack.pop()
      function_buffer.append(acc_var)
      continue

    take_match = re_take.search(line)
    if take_match and gather_stack:
      take_val = take_match.group(1).strip()
      acc_var = gather_stack[-1]
      line = f"AAdd({acc_var}, {take_val})"

    if re_scope_in.search(line):
      scope_counter += 1
      scope_stack.append(scope_counter)
      scope_vars[scope_counter] = set()
      scope_var_mangling[scope_counter] = {}
      curr_scope = scope_stack[-1]
      
    let_dor_match = re_let_defined_or.search(line)
    dor_match = re_defined_or.search(line)
    
    if let_dor_match:
      var_name = let_dor_match.group(1)
      default_expr = let_dor_match.group(2).strip()
      mangled = register_variable(var_name, curr_scope)
      line = f"If {mangled} == Nil\n  {mangled} := {default_expr}\nEndIf"
    elif dor_match:
      var_name = dor_match.group(1)
      default_expr = dor_match.group(2).strip()
      var_lower = var_name.lower()
      mangled = None
      for s_id in scope_stack:
        if var_lower in scope_vars[s_id]:
          mangled = scope_var_mangling[s_id][var_lower]
          break
      if not mangled:
        raise SyntaxError(f"Line {idx+1}: Variable '{var_name}' used with '?=' without prior declaration.")
      line = f"If {mangled} == Nil\n  {mangled} := {default_expr}\nEndIf"
    else:
      let_match = re_let.search(line)
      if let_match:
        var_name = let_match.group(1)
        mangled = register_variable(var_name, curr_scope)
        line = re_let.sub(f"{mangled} :=", line, count=1)
      else:
        assign_match = re_assign.search(line)
        if assign_match:
          var_name = assign_match.group(1)
          var_lower = var_name.lower()
          if var_lower not in reserved_words:
            declared = False
            for s_id in scope_stack:
              if var_lower in scope_vars[s_id]:
                declared = True
                break
            if not declared:
              raise SyntaxError(f"Line {idx+1}: Variable '{var_name}' used without declaration. Use 'let {var_name} := ...'.")

    with_match = re_with_start.search(line)
    if with_match:
      expr = with_match.group(1).strip()
      temp_var = f"__with_val_{scope_counter}_{temp_var_counter}"
      temp_var_counter += 1
      hoisted_vars.add(temp_var)
      
      with_stack.append({
        "target": temp_var, 
        "type": "with", 
        "has_branch": True,
        "has_otherwise": False,
        "line_idx": idx + 1
      })
      line = f"{temp_var} := {expr}\nIf {temp_var} != Nil"
      function_buffer.append(line)
      continue

    orwith_match = re_orwith.search(line)
    if orwith_match and with_stack:
      active_with = with_stack[-1]
      expr = orwith_match.group(1).strip()
      target = active_with["target"]
      line = f"{target} := {expr}\nElseIf {target} != Nil"
      function_buffer.append(line)
      continue

    without_match = re_without_start.search(line)
    if without_match:
      expr = without_match.group(1).strip()
      temp_var = f"__without_val_{scope_counter}_{temp_var_counter}"
      temp_var_counter += 1
      hoisted_vars.add(temp_var)
      
      with_stack.append({"target": temp_var, "type": "without"})
      line = f"{temp_var} := {expr}\nIf {temp_var} == Nil"
      function_buffer.append(line)
      continue

    given_match = re_given_start.search(line)
    if given_match:
      expr = given_match.group(1).strip()
      alias_user = given_match.group(2)
      temp_var = f"__given_val_{scope_counter}_{temp_var_counter}"
      temp_var_counter += 1
      hoisted_vars.add(temp_var)
      
      alias_mangled = register_variable(alias_user, curr_scope) if alias_user else None
      with_stack.append({
        "target": temp_var, 
        "type": "given", 
        "has_branch": False,
        "alias_mangled": alias_mangled
      })
      
      if alias_mangled:
        line = f"{temp_var} := {expr}\n  {alias_mangled} := {temp_var}"
      else:
        line = f"{temp_var} := {expr}"
      function_buffer.append(line)
      continue

    when_match = re_when_start.search(line)
    if when_match and with_stack and with_stack[-1]["type"] == "given":
      active_block = with_stack[-1]
      raw_cond = when_match.group(1).strip()
      target = active_block["target"]
      full_cond = parse_when_condition(target, raw_cond)
      
      if active_block["has_branch"]:
        line = f"ElseIf {full_cond}"
      else:
        line = f"If {full_cond}"
        active_block["has_branch"] = True
      function_buffer.append(line)
      continue

    otherwise_match = re_otherwise_start.search(line)
    if otherwise_match and with_stack:
      active_block = with_stack[-1]
      if active_block["type"] == "with":
        active_block["has_otherwise"] = True
      line = "Else"
      function_buffer.append(line)
      continue

    if re_endwith.search(line) and with_stack:
      active_block = with_stack.pop()
      if active_block["type"] == "with" and not active_block["has_otherwise"]:
        raise SyntaxError(f"Line {active_block['line_idx']}: 'with' block requires an 'otherwise' fallback clause.")
      line = "EndIf"
      function_buffer.append(line)
      continue
    if re_endwithout.search(line) and with_stack:
      with_stack.pop()
      line = "EndIf"
      function_buffer.append(line)
      continue
    if re_endgiven.search(line) and with_stack and with_stack[-1]["type"] == "given":
      with_stack.pop()
      line = "EndIf"
      function_buffer.append(line)
      continue

    line = transpile_feed_chains(line, curr_scope, idx)
    line = transpile_optional_chaining(line)
    line = transpile_safe_pipelines(line)
    line = transpile_xtpl_print(line)

    ret_match = re_postfix_return.match(stripped)
    exec_match = re_postfix_exec.match(stripped)
    gen_match = re_postfix_general.match(stripped)

    if ret_match:
      val = ret_match.group("val").strip()
      cond = ret_match.group("cond").strip()
      ret_expr = f"Return {val}" if val else "Return"
      defers = "\n".join([f"  {d}" for d in reversed(defer_stack)])
      line = f"If {cond}\n{defers}\n  {ret_expr}\nEndIf"
    elif re_explicit_return.match(stripped):
      defers = "\n".join([f"  {d}" for d in reversed(defer_stack)])
      line = f"{defers}\n{line}"
    elif exec_match:
      body = exec_match.group("body").strip()
      cond = exec_match.group("cond").strip()
      line = f"If {cond}\n  {body}\nEndIf"
    elif gen_match and not stripped.upper().startswith(("IF", "WHILE", "FOR", "ELSE")):
      body = gen_match.group("body").strip()
      kw = gen_match.group("kw").upper()
      cond = gen_match.group("cond").strip()
      if kw == "IF":
        line = f"If {cond}\n  {body}\nEndIf"
      elif kw == "WHILE":
        line = f"While {cond}\n  {body}\nEndDo"

    def resolve_identifier(match):
      word = match.group(0)
      word_lower = word.lower()
      if word_lower in reserved_words:
        return word
      for s_id in reversed(scope_stack):
        if word_lower in scope_vars[s_id]:
          return scope_var_mangling[s_id][word_lower]
      return word

    processed_line = re.sub(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', resolve_identifier, line)
      
    for sub_line in processed_line.splitlines():
      function_buffer.append(sub_line)
    
    if re_scope_out.search(line):
      if len(scope_stack) > 1:
        scope_stack.pop()
        
  flush_function(len(lines))
  return "\n".join(out_lines)

if __name__ == "__main__":
  if len(sys.argv) < 3:
    print("Usage: python xtpl_transpiler.py <input.xtpl> <output.prg>")
    sys.exit(1)
  with open(sys.argv[1], 'r', encoding='utf-8') as f:
    code = f.read()
  with open(sys.argv[2], 'w', encoding='utf-8') as f:
    f.write(transpile(code))

# --------------------------------------------------------------------------------
# the end
