import json
from lark import Lark, Transformer, Tree, Token
from lark.reconstruct import Reconstructor
from lark.visitors import v_args
from copy import deepcopy
from collections import ChainMap
from numbers import Number
import sys

def is_simple(entry):
  if isinstance(entry, list):
    return len(entry) == 0
  if isinstance(entry, dict):
    return len(entry) == 0
  return True

def is_short(entry, indent):
  return len(json.dumps(entry)) + indent < 80

def hdumps(entry, *, _current_indent=0):
  if is_short(entry, _current_indent):
    return json.dumps(entry)
  if isinstance(entry, list) and entry:
    result = "[ " + hdumps(entry[0], _current_indent=_current_indent+2)
    for x in entry[1:]:
      result += "\n" + " " * _current_indent + ", "
      result += hdumps(x, _current_indent=_current_indent+2)
    result += "\n" + " " * _current_indent + "]"
    return result
  if isinstance(entry, dict) and entry:
    result = "{ "
    is_first = True
    for k in entry.keys():
      if not is_first:
        result += "\n" + " " * _current_indent + ", "
      result += json.dumps(k) + ":"
      if is_simple(entry[k]):
        result += " " + json.dumps(entry[k])
      elif is_short(entry[k], _current_indent + len(json.dumps(k)) + 4):
        result += " " + json.dumps(entry[k])
      else:
        result += "\n" + " " * _current_indent + "  "
        result += hdumps(entry[k], _current_indent=_current_indent+2)
      is_first = False
    result += "\n" + " " * _current_indent + "}"
    return result
  return json.dumps(entry)


parser = Lark.open("just-nj.lark", start=["start_expr"], maybe_placeholders=False)

def order_entries(obj, keys):
    result = {}
    for k in keys:
        if k in obj:
            result[k] = obj[k]
    for k in obj.keys():
        if k not in keys:
            result[k] = obj[k]
    return result

class NotPresent():
    pass

class JustExpTransformer(Transformer):
    def start_expr(self, start):
        return dict(reversed(dict(ChainMap(*start)).items()))

    def expression_def(self, definition):
        definition = definition[1:2] + definition[0:1] + definition[2:]
        name = definition[0]
        expression = definition[-1]
        definition = definition[1:-1]
        body = dict(ChainMap(*definition), **{"expression": expression} )
        
        return {name : order_entries(body, ['doc', 'vars', 'vars_doc', 'imports', 'expression'])}

    def using_block(self, arg):
        uses = dict(reversed(dict(ChainMap(*arg)).items()))
        return {"imports": uses}

    def using(self, use):
        return {use[0] : use[1]}

    def name(self, name):
        (name,) = name
        return name

    def ESCAPED_STRING(self, s):
        return json.loads(s.value)

    def plain_variable(self, name):
        (name,) = name
        return { "type": "var", "name": name}

    def variable_with_default(self, definition):
        (name, default, ) = definition
        return {"type": "var", "name": name, "default": default}

    def expression(self, i):
        (i, ) = i
        return i

    def exp_args(self, args):
        return {"vars": args} if args else {}

    def qualified_target(self, target):
        return target

    def local_target(self, target):
        (target,) = target
        return target

    def function(self, arg):
        name = [{"type": arg[0]}]
        keyword_args = list(filter(lambda x: isinstance(x,Tree), arg[1:]))
        keyword_args = list(reversed(list(map(lambda x: {x.children[0]: x.children[1]}, keyword_args))))
        exprs = list(filter(lambda x: not isinstance(x,Tree), arg[1:]))
        exprs = list(map(lambda a: {f"${a[0] + 1}": a[1]}, zip(range(len(exprs)), exprs)))
        return dict(ChainMap(*(exprs + keyword_args + name)))


    def LITERAL_STRING(self, s):
        return s[2:-1]

    def singleton_map(self, m):
        return {"type": "singleton_map", "key": m[0], "value": m[1]}

    def for_each(self, f):
        if len(f) == 3:
            return {"type": "foreach", "var": f[0], "range": f[1], "body": f[2]}
        else:
            return {"type": "foreach", "range": f[0], "body": f[1]}

    @v_args(inline=True)
    def for_map_bind(self, b = NotPresent()):
        return b

    @v_args(inline=True)
    def for_map(self, k, v, r, body):
        k = {"var_key": k} if not isinstance(k, NotPresent) else {}
        v = {"var_val": v} if not isinstance(v, NotPresent) else {}
        return order_entries(dict(**{"type": "foreach_map", "range": r, "body": body}, **k, **v),
                             ['type', 'range', 'var_key', 'var_val', 'body'])

    @v_args(inline=True)
    def foldl_start(self, s = NotPresent()):
        return s

    @v_args(inline=True)
    def foldl(self, r, start, acc, v, body):
        acc = {"accum_var": acc} if not isinstance(acc, NotPresent) else {}
        v = {"var": v} if not isinstance(v, NotPresent) else {}
        start = {"start": start} if not isinstance(start, NotPresent) else {}
        return order_entries(dict(**{"type": "foldl", "range": r, "body": body}, **acc, **v, **start)
                            , ['type', 'var', 'accum_var', 'range', 'body'])

    def EMPTY_MAP(self, _):
        return {"type": "empty_map"}

    def expr_doc(self, docs):
        vars_doc = dict(reversed(dict(ChainMap(*[d["vars_doc"] for d in docs if "vars_doc" in d])).items()))
        return dict(ChainMap(*docs),
                    **({"vars_doc": vars_doc} if vars_doc else {}))

    @v_args(inline=True)
    def EXPR_DOC_MAIN(self, doc):
        return {"doc": [s[2:] for s in doc.value.splitlines()]}

    @v_args(inline=True)
    def expr_doc_var(self, fieldname, docstring):
        return {"vars_doc":
                {fieldname: [s[2:] for s in ("  " + docstring.value).splitlines()]}}

    def let(self, c):
        let_binds = c[:-1]
        body = c[-1]
        return {"type": "let*", "bindings": let_binds, "body": body}

    @v_args(inline=True)
    def let_bind(self, var, expr):
        return [var, expr]

    @v_args(inline=True)
    def if_expr(self, cond, then, el=NotPresent()):
        return dict(**{"type": "if", "cond": cond, "then": then},
                    **({"else": el} if not isinstance(el, NotPresent) else {}))


    @v_args(inline=True)
    def clause(self, cond, clause):
        return [cond, clause]

    def cond_clauses(self, clauses):
        return clauses

    @v_args(inline=True)
    def cond(self, clauses, default):
        return dict(**{"type": "cond", "cond": clauses},
                    **default)

    def case(self, cs):
        if len(cs) == 3:
            cases = dict(ChainMap(*[{ k: v} for k, v in cs[1]]))
            return dict(**{"type": "case", "expr": cs[0]}, **({"case": cases} if cases else {}), **cs[2])
        else: 
            return dict(**{"type": "case"}, **cs[0])

    def case_star(self, cs):
        if len(cs) == 3:
            return dict(**{"type": "case*", "expr": cs[0]}, **({"case": cs[1]} if cs[1] else {}), **cs[2])
        else: 
            return dict(**{"type": "case*"}, **cs[0])

    @v_args(inline=True)
    def optional_default(self, default=NotPresent()):
        return ({"default": default} if not isinstance(default, NotPresent) else {})

    def BOOL(self, b):
        return b == "true"

    def NULL(self, _):
        return None

    def NUMBER(self, n):
        return float(n)

    list = list

function_names = ["nub_right"
             , "basename"
             , "keys"
             , "values"
             , "range"
             , "enumerate"
             , "++"
             , "map_union"
             , "join_cmd"
             , "json_encode"
             , "and"
             , "or"
             , "change_ending"
             , "join"
             , "escape_chars"
             , "to_subdir"
             , "context"
             , "assert_non_empty"
             , "disjoint_map_union"
             , "DEP_ARTIFACTS"
             , "DEP_RUNFILES"
             , "DEP_PROVIDES"
             , "FIELD"
             , "env"
             , "fail"
             , "CALL_EXPRESSION"
                  , "RESULT"
                  , "ACTION"
                  , "TREE"
                  , "BLOB"
                  , "lookup"
                  ]


def tt(n, a):
    return Tree(tr(n), a)

def tokenize_exp(e):
    return tt('expression', [tokenize(e)])

def tr(r):
    return Token('RULE', r)

def tokenize_name(n):
    return tt('name', [Token('ESCAPED_STRING', json.dumps(n))])

def tokenize(t):
    if isinstance(t, dict):
        assert( 'type' in t)
        type = t['type']
        if type == 'singleton_map':
            assert('key' in t)
            assert('value' in t)
            key = tokenize_exp(t['key'])
            value = tokenize_exp(t['value'])
            return Tree(tr('singleton_map'), [key, value])
        elif type == 'empty_map':
            return Token('EMPTY_MAP', '{}')
        elif type == 'var':
            assert('name' in t)
            name = tokenize_name(t['name'])
            if 'default' in t:
                default = tokenize_exp(t['default'])
                return Tree('variable_with_default', [name, default])
            else:
                return Tree('plain_variable', [name])
        elif type in function_names:
            fname = Token('FUNCTION_NAME', t['type'])
            del t['type']
            positional = []
            keyword_args = []
            for i in [1, 2]:
                if f"${i}" in t:
                    positional.append(tokenize_exp(t[f"${i}"]))
                    del t[f"${i}"]
            for k, v in t.items():
                name = tokenize_name(k)
                value = tokenize_exp(v)
                keyword_args.append(tt('keyword_arg', [name, value]))
            return tt('function', [fname] + keyword_args + positional)
        elif type == 'foldl':
            assert('range' in t)
            assert('body' in t)
            range = tokenize_exp(t['range'])
            start = tt('foldl_start', [tokenize_exp(t['start'])] if 'start' in t else [])
            acc_var = tt('for_map_bind', [tokenize_name(t['accum_var'])] if 'accum_var' in t else [])
            var = tt('for_map_bind', [tokenize_name(t['var'])] if 'var' in t else [])
            body = tokenize_exp(t['body'])
            return tt('foldl', [range, start, acc_var, var, body])
        elif type == 'foreach':
            assert('range' in t)
            assert('body' in t)
            range = [ tokenize_exp(t['range']) ]
            body = [ tokenize_exp(t['body']) ]
            var = [tokenize_name(t['var'])] if 'var' in t else []
            return tt('for_each', var + range + body)
        elif type == 'foreach_map':
            assert('range' in t)
            assert('body' in t)
            range = tokenize_exp(t['range'])
            key = tt('for_map_bind', [tokenize_name(t['var_key'])] if 'var_key' in t else [])
            val = tt('for_map_bind', [tokenize_name(t['var_val'])] if 'var_val' in t else [])
            body  = tokenize_exp(t['body'])
            return tt('for_map', [key, val, range, body])
        elif type == "let*":
            assert('body' in t)
            body = [tokenize_exp(t['body'])]
            binding = lambda b: tt('let_bind', [tokenize_name(b[0]), tokenize_exp(b[1])])
            bindings = [binding(b) for b in t['bindings']] if 'bindings' in t else []
            return tt('let', bindings + body)
        elif type == 'case':
            cond_clause = lambda k, v: tt('clause', [tokenize_exp(k), tokenize_exp(v)])
            expr = [tokenize_exp(t['expr'])] if 'expr' in t else []
            cond_clauses = [tt('cond_clauses',
                              [cond_clause(k, v) for k, v in t['case'].items()])] if 'case' in t else []
            default = [tt('optional_default', [tokenize_exp(t['default'])] if 'default' in t else [])]
            return tt('case', expr + cond_clauses + default)
        elif type == "case*":
            expr = [tokenize_exp(t['expr'])] if 'expr' in t else []
            cond_clause = lambda c: tt('clause', [tokenize_exp(c[0]), tokenize_exp(c[1])])
            cond_clauses = [tt('cond_clauses',
                            [cond_clause(c) for c in t['case']])] if 'case' in t else []
            default = [tt('optional_default', [tokenize_exp(t['default'])] if 'default' in t else [])]
            return tt('case_star', expr + cond_clauses + default)
        elif type == 'if':
            assert('cond' in t)
            assert('then' in t)
            cond = [tokenize_exp(t['cond'])]
            then = [tokenize_exp(t['then'])]
            el   = [tokenize_exp(t['else'])] if 'else' in t else []
            return tt('if_expr', cond + then + el)
        elif type == 'cond':
            assert('cond' in t)
            cond_clause = lambda c: tt('clause', [tokenize_exp(c[0]), tokenize_exp(c[1])])
            cond_clauses = tt('cond_clauses', [cond_clause(c) for c in t['cond']])
            default = tt('optional_default', [tokenize_exp(t['default'])] if 'default' in t else [])
            return tt('cond', [cond_clauses, default])
        else:
            print("Missing: %r" % (t,))
        
    elif isinstance(t, list):
        return Tree(tr('list'), [tokenize_exp(x) for x in t])
    elif isinstance(t, str):
        return Token("LITERAL_STRING", "s" + json.dumps(t))
    elif isinstance(t, bool):
        if t:
            return Token("BOOL", 'true')
        else:
            return Token('BOOL', 'false')
    elif isinstance(t, Number):
        return Token('NUMBER', str(t))
    elif t is None:
        return Token("NULL", 'null')
    else:
        print("Missing: %r" % (t,))

def tokenize_target(t):
    if isinstance(t, str):
        return Tree('local_target', [Token('ESCAPED_STRING', json.dumps(t))])
    else:
        return Tree('qualified_target', [Token('ESCAPED_STRING', json.dumps(s)) for s in t])

def tokenize_expr_def(e, name):
    name = tokenize_name(name)
    assert('expression' in e)
    expr_docs = [Token('EXPR_DOC_MAIN', "# " + "\n# ".join(e['doc']) + "\n")] if 'doc' in e else []
    expr_var = lambda v: Token('EXPR_DOC_V', "\n* ".join(v) + "\n")
    expr_vars = [tt('expr_doc_var', [tokenize_name(n), expr_var(v)])
                 for n, v in e['vars_doc'].items()] if 'vars_doc' in e else []
    doc = tt('expr_doc', expr_docs + expr_vars)
    expr_args = tt('exp_args', [tokenize_name(x) for x in e['vars']] if 'vars' in e else [])
    exp = tokenize_exp(e['expression'])
    usings = [tt('using_block', [tt('using', [tokenize_name(k), tokenize_target(v)])
                                 for k, v in e['imports'].items()])] if 'imports' in e else []
    return tt("expression_def", [doc] + [name] + [expr_args] + usings + [exp])
    

def tokenize_exprs(es):
    es = deepcopy(es)
    return tt("start_expr", [tokenize_expr_def(e, name) for name, e in es.items()])



def postproc(items):
    printed_newlines = False
    after_exp = False

    for item in items:
        if not printed_newlines:
            if item == 'exp':
                yield "\n\n"
            elif (isinstance(item, Token) and item.type == 'EXPR_DOC_MAIN') or item == '*v ':
                yield "\n\n"
                printed_newlines = True

        if item == 'exp':
            printed_newlines = False
            after_exp = True
        if item == 'using':
            yield '  \n '
        if item == '=' and after_exp:
            yield '\n'
            after_exp = False
        if item == 'in':
            yield '\n'


        yield item
        yield ' '
        if item == 'in':
            yield '\n'

recon = Reconstructor(parser)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1].startswith('e'):
            print(hdumps(JustExpTransformer().transform(parser.parse(sys.stdin.read()))))
        else:
            print(recon.reconstruct(tokenize_exprs(json.load(sys.stdin)), postproc))
 
