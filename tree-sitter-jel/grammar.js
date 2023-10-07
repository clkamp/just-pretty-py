module.exports = grammar({
  name: 'jel',

  rules: {
    expression_file: $ => repeat($.expression_def),

    expression_def: $ => seq(
      optional($.expr_doc),
      repeat($.var_doc),
      'exp',
      field('name', $.name),
      field('parameters', $.exp_args),
      field('usings', optional($.usings)),
      "=",
      field('body', $._expression)
    ),

    var_doc: $ => seq(
      '*v ',
      field('name', $.name),
      '-> ',
      field('doc', $.var_doc_content)
      ),
    var_doc_content: $ => /[^\n]+\n(\* [^\n]*\n|\*\n)*/,

    expr_doc: $ => seq(
	      "# ",
	      /[^\n]+\n(# [^\n]*\n|#\n)*/
      ),

    exp_args: $ => seq(
	    '(',
	    repeat(seq($.name, optional(','))),
            ')'),

    usings: $ => seq(
      'using',
      repeat($.using)
      ),
    using: $ => seq(
      field('name', $.name),
      '=>',
      field('target', $._target)
    ),




    _expression:  $ => choice(
      $._literal,
      $.list,
      $.singleton_map,
      $.variable,
      $.func,
      $.dollar_func,
      $.for_each,
      $.for_map,
      $.foldl,
      $.variable_binding,
      $.case_clause,
      $.case_star,
      $.if_expr,
      $.cond
    ),

    // Literals

    _literal: $=> choice(
      $.empty_map,
      $.literal_string,
      $.bool,
      $.nul,
      $.number
    ),

    empty_map: $=> seq('{', '}'),
    literal_string: $=> seq('s"', $._string_content, '"'),
    bool: $=> choice('true', 'false'),
    nul: $=> 'null',
    number: $=> /\d+/,

    // Constructors
    list: $=> seq('[', optional(seq($._expression, repeat(seq(',', $._expression)))), ']'),
    singleton_map: $=> seq('{', field('key', $._expression), ':', field('value', $._expression), '}'),

    name: $=> choice(
      /[a-zA-Z0-9_-]+/,
      $._string
    ),

    _target: $=> choice(
      $.local_target,
      $.qualified_target
    ),

    local_target: $=> $._string,
    qualified_target: $=> seq(
      "[",
      $._string,
      repeat1(seq(",", $._string)),
      "]"
    ),

    // Variables
    variable: $=> seq(field('name', $.name), optional(seq("?=", field('default', $._expression)))),

    // Function
    function_name: $=> choice(
      'nub_right',
      'basename',
      'keys',
      'values',
      'range',
      'enumerate',
      '++',
      'map_union',
      'join_cmd',
      'json_encode',
      'and',
      'or',
      'change_ending',
      'join',
      'escape_chars',
      'to_subdir',
      'context',
      'assert_non_empty',
      'disjoint_map_union',
      'DEP_ARTIFACTS',
      'DEP_RUNFILES',
      'DEP_PROVIDES',
      'FIELD',
      'env',
      'fail',
      'CALL_EXPRESSION',
      'RESULT',
      'ACTION',
      'TREE',
      'BLOB',
      'lookup'
    ),

    keyword_arg: $=> seq(field('name', $.name), '=', field('value', $._expression)),
    func: $=> seq(
      field('name', $.function_name),
      '(',
      commaSep(choice($.keyword_arg, $._expression)),
      ')'
    ),

    dollar_func: $=> seq(
      field('name', $.function_name),
      '$',
      field('body', $._expression)
    ),

    // Iterators
    for_each: $=> seq(
      "for",
      optional(field('runtime_var', $.name)),
      ":",
      field('iterator', $._expression),
      field('body', $._expression)
    ),

    for_map: $=> seq(
      'for',
      optional(field('runtime_key', $.name)),
      ',',
      optional(field('runtime_var', $.name)),
      ":",
      field('iterator', $._expression),
      field('body', $._expression)
    ),

    foldl: $=> seq(
      'foldl',
      field('iterator', $._expression),
      optional(field('start', $._expression)),
      '\\',
      optional(field('accum_var', $.name)),
      ',',
      optional(field('runtim_var', $.name)),
      ':',
      field('body', $._expression)
    ),

    // Bindings

    variable_binding: $=> seq(
      'let*',
      field('binds', repeat($.let_bind)),
      'in',
      field('body', $._expression)
    ),

    let_bind: $=> seq(
      field('name', $.name),
      '<-',
      field('binding', $._expression),
    ),

    // Conditionals

    clause: $=> seq(
      field('condition', $._expression),
      '->',
      field('result', $._expression)
    ),

    case_clause: $=> seq(
      'case',
      optional(field('expr', $._expression)),
      optional(field('clauses', repeat($.clause))),
      choice('end',
                      seq('=>', field('default', $._expression))
            )
    ),

    case_star: $=> seq(
      'case*',
      optional(field('expr', $._expression)),
      optional(field('clauses', repeat($.clause))),
      choice('end',
                      seq('=>', field('default', $._expression))
            )
    ),

    if_expr: $=> seq(
      'if',
      field('condition', $._expression),
      'then',
      field('then', $._expression),
      choice('end',
             seq('else', field('else', $._expression))
            )
    ),

    cond: $=> seq(
      'cond',
      optional(field('clauses', repeat($.clause))),
      choice('end',
                      seq('=>', field('default', $._expression))
            )
    ),



    // String types

    _string: $ => choice(
      seq('"', '"'),
      seq('"', $._string_content, '"')
    ),

    _string_content: $=> repeat1(choice(
      token.immediate(prec(1, /[^\\"\n]+/)),
      $._escape_sequence
    )),

    _escape_sequence: $ => token.immediate(seq(
      '\\',
      /(\"|\\|\/|b|f|n|r|t|u)/
    ))

  }
});

function commaSep1(rule) {
  return seq(rule, repeat(seq(",", rule)))
}

function commaSep(rule) {
  return optional(commaSep1(rule))
}
