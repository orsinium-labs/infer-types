# infer-types

A CLI tool to automatically add type annotations into Python code.

The main scenario for using the tool is to help you with annotating a big and old codebase. It won't solve the task for you 100% but will definitely help you tremendously, because many of the functions in the real world have quite simple return types that are easy to infer automatically.

Features:

+ 100% automated, get a bunch of type annotations with no effort.
+ Unix-way, does only one job and does it well.
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
python3 -m pip install infer-types retype
```

This will also install retype which we're going to use to apply generated type annotations back to the code (see Usage below).

## Usage

First of all, run the tool:

```bash
python3 -m infer_types ./example/
```

It will infer types for all code in the `example` directory and save [stub files](https://mypy.readthedocs.io/en/stable/stubs.html) inside of `types` directory.

The next thing you need to do is to apply the stub files back to the code. For that, we're going to use [retype](https://github.com/ambv/retype):

```bash
retype -it ./example/ ./example/
```

The infer-types tool uses the new fancy syntax for type annotations introduced in Python 3.10. So, instead of `Optional[str]` it will emit `str | None`. If your code is supposed to run on an older version of Python, add `from __future__ import annotations` at the beginning of each file. It will solve the issue and also make startup of your app faster.

See [awesome-python-typing](https://github.com/typeddjango/awesome-python-typing) for more tools to help you with annotating your code.

## How it works

+ Most of heuristics live in [astypes](https://github.com/orsinium-labs/astypes) package. Check it out learn more about the main inference logic.
+ If the same method is defined in a base class, copy the type annotations from there.
+ If there are no return statements returning a value, the return type is `None`.
+ If there is a `yield` statement, the return type is `typing.Iterator`.
