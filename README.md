# infer-types

A CLI tool to automatically add type annotations into Python code.

The main scenario for using the tool is to help you with annotating a big and old codebase. It won't solve the task for you 100% but will definitely help you tremendously, because many of the functions in the real world have quite simple return types that are easy to infer automatically.

Features:

+ 100% automated, get a bunch of type annotations with no effort.
+ 100% static, all types are inferred without running the code.
+ A lot of heuristics and smart inference.
+ Actively uses [typeshed](https://github.com/python/typeshed) to find annotations for unannotated dependencies.

## Example

Let's say, you have the following method:

```python
class Database:
    def users_count(self):
        return len(self.users)
```

Since `len` always returns `int`, `infer-types` is able to infer the return type of the method. So, after running the tool, the code will look like this:

```python
class Database:
    def users_count(self) -> int:
        return len(self.users)
```

## Installation

```bash
python3 -m pip install infer-types
```

## Usage

```bash
python3 -m infer_types ./example/
```

The tool will add new import statements that can be duplicated and are located not at the top of the file. To fix it, run [isort](https://github.com/PyCQA/isort):

```bash
python3 -m isort ./example/
```

The infer-types tool uses the new fancy syntax for type annotations introduced in Python 3.10. So, instead of `Optional[str]` it will emit `str | None`. If your code is supposed to run on an older version of Python, add `from __future__ import annotations` at the beginning of each file. It will solve the issue and also make startup of your app faster. You can also do that with isort:

```bash
python3 -m isort --add-import 'from __future__ import annotations' ./example/
```

See [awesome-python-typing](https://github.com/typeddjango/awesome-python-typing) for more tools to help you with annotating your code.

## How it works

+ Most of heuristics live in [astypes](https://github.com/orsinium-labs/astypes) package. Check it out learn more about the main inference logic.
+ If the same method is defined in a base class, copy the type annotations from there.
+ If there are no return statements returning a value, the return type is `None`.
+ If there is a `yield` statement, the return type is `typing.Iterator`.
+ In some cases, the return type can be guessed from the function name. For example, `is_open` function is assumed to return `bool` because it starts with `is_`.

You can run only a specific heuristic using the `--only` flag.
