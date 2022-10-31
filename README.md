# Just pretty

A proof of concept for a syntax view for just `EXPRESSION` files.
The syntax can be transformed to and from the JSON representation.
However, when converting from JSON there is currently no pretty printing.

An example of a (manually) pretty printed `EXPRESSION` file[^1] is shown in
`rules.CC.EXPRESSION.jnj`.

The conversion tool requires python3 with the `lark` library[^2] installed and
reads from stdin and prints the converted version to stdout. The first argument
determines the direction of conversion: use `e` for conversion to JSON from the
view syntax and `d` for the opposite direction.


[^1]: Converted from  https://github.com/just-buildsystem/justbuild/blob/f875e1bcbe79ee8752612a5bfe9f1814f52f3ad1/rules/CC/EXPRESSIONS
[^2]: https://github.com/lark-parser/lark
