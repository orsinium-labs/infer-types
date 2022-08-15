# infer-types

A CLI tool to automatically add type annotations into Python code.

The main scenario for using the tool is to help you with annotating a big and old codebase. It won't solve the task for you 100% but will definitely help you tremendously, because many of the functions in the real world have quite simple return types that are easy to infer automatically.

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

See [awesome-python-typing](https://github.com/typeddjango/awesome-python-typing) for more tools to help you with annotating your code.
