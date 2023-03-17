from __future__ import annotations

from types import MappingProxyType

from astypes import Type


KNOWN_NAMES = MappingProxyType({
    'dumps': 'str',
    'exists': 'bool',
    'contains': 'bool',
    'count': 'int',
    'size': 'int',
})
REMOVE_PREFIXES = ('as_', 'to_', 'get_')
BOOL_PREFIXES = ('is_', 'has_', 'should_', 'can_', 'will_', 'supports_')

t = Type.new
tself = t('Self', module='typing')
# https://docs.python.org/3/reference/datamodel.html
MAGIC_METHODS = MappingProxyType(dict(
    __contains__=t('bool'),
    __del__=t('None'),
    __delete__=t('None'),
    __dir__=t('list', args=[t('str')]),
    __exit__=t('Union', args=[t('bool'), t('None')]),
    __format__=t('str'),
    __hash__=t('int'),
    __index__=t('int'),
    __init__=t('None'),
    __init_subclass__=t('None'),
    __instancecheck__=t('bool'),
    __iter__=t('Iterator', module='typing'),
    __len__=t('int'),
    __length_hint__=t('int'),
    __new__=t('type'),
    __nonzero__=t('bool'),
    __repr__=t('str'),
    __reversed__=t('Iterator', module='typing'),
    __set__=t('None'),
    __set_name__=t('None'),
    __subclasscheck__=t('bool'),

    # convert to types
    __bool__=t('bool'),
    __bytes__=t('bytes'),
    __complex__=t('complex'),
    __float__=t('float'),
    __int__=t('int'),
    __str__=t('str'),

    # async/await
    __aiter__=t('AsyncIterator', module='typing'),
    __await__=t('Iterator', module='typing'),
    __aexit__=t('Union', args=[t('bool'), t('None')]),

    # comparison
    __eq__=t('bool'),
    __ne__=t('bool'),
    __ge__=t('bool'),
    __gt__=t('bool'),
    __le__=t('bool'),
    __lt__=t('bool'),

    # arithmetic
    __add__=tself,
    __and__=tself,
    __divmod__=tself,
    __floordiv__=tself,
    __lshift__=tself,
    __matmul__=tself,
    __mod__=tself,
    __mul__=tself,
    __or__=tself,
    __pow__=tself,
    __rshift__=tself,
    __sub__=tself,
    __truediv__=tself,
    __xor__=tself,

    # reversed arithmetic
    __radd__=tself,
    __rsub__=tself,
    __rmul__=tself,
    __rmatmul__=tself,
    __rtruediv__=tself,
    __rfloordiv__=tself,
    __rmod__=tself,
    __rdivmod__=tself,
    __rpow__=tself,
    __rlshift__=tself,
    __rrshift__=tself,
    __rand__=tself,
    __rxor__=tself,
    __ror__=tself,

    # in-place arithmetic
    __iadd__=tself,
    __isub__=tself,
    __imul__=tself,
    __imatmul__=tself,
    __itruediv__=tself,
    __ifloordiv__=tself,
    __imod__=tself,
    __ipow__=tself,
    __ilshift__=tself,
    __irshift__=tself,
    __iand__=tself,
    __ixor__=tself,
    __ior__=tself,

    # unary operators
    __neg__=tself,
    __pos__=tself,
    __abs__=tself,
    __invert__=tself,

    # number rounding operations
    __round__=t('int'),
    __trunc__=t('int'),
    __floor__=t('int'),
    __ceil__=t('int'),
))
