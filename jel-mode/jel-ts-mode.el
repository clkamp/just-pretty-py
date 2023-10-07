;;; jel-mode.el A major mode for jel -*- lexical-binding: t; -*-
;;
;; Copyright (C) 2023 Christian Lütke Stetzkamp
;;
;; Author: Christian Lütke Stetzkamp <christian@lkamp.de>
;; Maintainer: Christian Lütke Stetzkamp <christian@lkamp.de>
;; Created: Oktober 03, 2023
;; Modified: Oktober 03, 2023
;; Version: 0.0.1
;; Keywords: abbrev bib c calendar comm convenience data docs emulations extensions faces files frames games hardware help hypermedia i18n internal languages lisp local maint mail matching mouse multimedia news outlines processes terminals tex tools unix vc wp
;; Homepage: https://github.com/clkamp/jel-mode
;; Package-Requires: ((emacs "24.3"))
;;
;; This file is not part of GNU Emacs.
;;
;;; Commentary:
;;
;;
;;
;;; Code:

(require 'treesit)

(defvar jel-ts-mode--keywords
  '("exp" "using" "for" "foldl" "let*" "in" "case" "case*" "if" "then" "else" "end" "cond")
  "Jel keywords for tree-sitter font-locking.")

(defvar jel-ts-mode--font-lock-settings
  (treesit-font-lock-rules
   :language 'jel
   :feature 'keyword
   `([,@jel-ts-mode--keywords] @font-lock-keyword-face)

   :language 'jel
   :feature 'bracket
   '(["[" "]" "(" ")" "{" "}"] @font-lock-bracket-face)

   :language 'jel
   :feature `delimiter
   '((["," ":" "\\"]) @font-lock-delimiter-face)

   :language 'jel
   :feature 'string
   '((literal_string) @font-lock-string-face)

   :language 'jel
   :feature 'doc
   '([(expr_doc) (var_doc)] @font-lock-doc-face)

   :language 'jel
   :feature 'function
   '((expression_def name: (_) @font-lock-function-name-face))

   :language 'jel
   :feature 'function-call
   '((function_name) @font-lock-function-call-face)

   :language 'jel
   :feature 'var
   '((name) @font-lock-variable-name-face)

   :language 'jel
   :feature 'error
   :override t
   '((ERROR) @font-lock-warning-face))
  "Tree-sitter font-lock settings.")



;;;#autoload
(define-derived-mode jel-ts-mode prog-mode "Jel"
  "A mode for a justbuild expression language."
  (when (treesit-ready-p 'jel)
    (treesit-parser-create 'jel)

    (setq-local treesit-font-lock-settings
                jel-ts-mode--font-lock-settings)
    (setq-local treesit-font-lock-feature-list
                '((keyword string bracket delimiter var doc function function-call)
                  (error)))

    (treesit-major-mode-setup)))

(provide 'jel-ts-mode)
;;; jel-ts-mode.el ends here
