[
 "exp"
 "using"
 "for"
 "foldl"
 "let*"
 "case"
 "case*"
 "if"
 "then"
 "end"
 "cond"
] @keyword
 (var_doc) @comment

 (name) @variable

(literal_string) @string

[
 (bool)
 (nul)
] @constant.buildin

(expression_def
  name: (name) @function)
