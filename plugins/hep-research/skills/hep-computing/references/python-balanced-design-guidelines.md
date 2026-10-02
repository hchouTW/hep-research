# Balanced Python Design Guidelines

When modifying or writing Python code, prefer a balanced style between
object-oriented and procedural programming. Follow established repository
conventions when they intentionally differ from this reference.

The examples assume Python 3.10 or later (they use `X | None` and built-in generics such as
`list[str]`).

The examples follow [PEP 8](https://peps.python.org/pep-0008/) and the
[Google Python Style Guide](https://google.github.io/styleguide/pyguide.html):
four-space indentation, `snake_case` functions and variables, `PascalCase`
class names, a single leading underscore for non-public attributes, and type
hints on public function signatures. Unlike the Google C++ Style Guide,
idiomatic Python embraces exceptions as the primary error-handling mechanism,
so this guide's error-handling section departs from its
[C++ counterpart](cpp-balanced-design-guidelines.md) accordingly.

## Contents

- [Core Principle](#core-principle)
- [Choosing Classes, Dataclasses, and Free Functions](#when-to-use-a-class)
- [Resource Management](#resource-management)
- [Inheritance, Protocols, and Polymorphism](#inheritance-protocols-and-polymorphism)
- [Encapsulation and State](#encapsulation-guidelines)
- [Error Handling](#error-handling)
- [Type Hints and Immutability](#type-hints-and-immutability)
- [Ownership and Reference Semantics](#ownership-and-reference-semantics)
- [Naming and Module Organization](#naming-guidance)
- [Testing and Generic Code](#testing-guidance)
- [Standard Library and Documentation](#standard-library-preference)
- [Design Checklist](#design-checklist)
- [Anti-Patterns Recap](#anti-patterns-to-avoid-recap)
- [Summary Rule](#summary-rule)

## Core Principle

Use classes to protect state, lifetime, ownership, resources, and invariants.

Use free functions to express algorithms, transformations, calculations, and
procedural workflows.

Do not force everything into classes. Do not write purely global-state
procedural code either.

The preferred style is simple, idiomatic, testable Python.

---

## When to Use a Class

Use a `class` when the code needs one or more of the following:

- Encapsulated state
- A clear lifetime
- Ownership of a resource
- Invariants that must be protected
- Context-manager behavior (`__enter__`/`__exit__`)
- Runtime polymorphism through a stable interface

Good examples:

```python
class File: ...
class Socket: ...
class BankAccount: ...
class Parser: ...
class Renderer: ...
class Order: ...
```

A class should represent a real concept in the domain or architecture, not
merely act as a folder for related functions.

Prefer a `class` when there is something meaningful to hide, validate,
protect, or manage.

Example:

```python
class BankAccount:
    def __init__(self, initial_balance: int) -> None:
        if initial_balance < 0:
            raise ValueError("initial_balance must not be negative")
        self._balance = initial_balance

    def deposit(self, amount: int) -> None:
        if amount <= 0:
            raise ValueError("amount must be positive")
        self._balance += amount

    def withdraw(self, amount: int) -> None:
        if amount <= 0 or amount > self._balance:
            raise ValueError("invalid withdrawal amount")
        self._balance -= amount

    @property
    def balance(self) -> int:
        return self._balance
```

In this example, the class is justified because it protects the invariant
that the balance must not become negative.

---

## When to Use a Dataclass

Use `@dataclass` (or `NamedTuple` for immutable, tuple-like data) for simple
passive data where public fields are clear, safe, and intentional.

Prefer this:

```python
from dataclasses import dataclass


@dataclass
class Point:
    x: float
    y: float
```

Avoid unnecessary getters and setters when there is no invariant to protect.

Avoid this unless validation or encapsulation is actually needed:

```python
class Point:
    def __init__(self, x: float, y: float) -> None:
        self._x = x
        self._y = y

    @property
    def x(self) -> float:
        return self._x

    @x.setter
    def x(self, value: float) -> None:
        self._x = value

    @property
    def y(self) -> float:
        return self._y

    @y.setter
    def y(self, value: float) -> None:
        self._y = value
```

A plain `@dataclass` is not a lesser choice than a hand-written class. In
Python, it is often the clearest choice for simple data types, and it gets
`__init__`, `__repr__`, and `__eq__` for free.

Use a dataclass when:

- The type is mainly a data carrier
- The fields are safe to expose
- There are no important invariants
- The type has no complex ownership responsibility
- Structural equality and a generated `__repr__` are desirable

Example:

```python
@dataclass
class Size:
    width: int
    height: int
```

If later the data needs validation or lifecycle management, it can be
refactored into a class, or fields can gain `__post_init__` validation before
promoting the type to a full class.

---

## When to Use Free Functions

Use module-level functions for algorithms, calculations, conversions, and
operations that do not need private access to an object.

Prefer this:

```python
import math
from dataclasses import dataclass


@dataclass
class Point:
    x: float
    y: float


def distance(a: Point, b: Point) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)
```

Do not put a function inside a class only because it is related to a type.

A function should usually remain a free function when:

- It does not need private access
- It does not modify object invariants
- It represents an algorithm rather than object behavior
- It can be tested independently
- It can operate on multiple compatible types (duck typing)

Use methods when the operation must preserve, validate, or modify the
object's internal invariant.

Example of a justified method:

```python
class Counter:
    def __init__(self) -> None:
        self._value = 0

    def increment(self) -> None:
        self._value += 1

    @property
    def value(self) -> int:
        return self._value
```

Example of a better free function:

```python
@dataclass
class Point:
    x: float
    y: float


def midpoint(a: Point, b: Point) -> Point:
    return Point(x=(a.x + b.x) / 2.0, y=(a.y + b.y) / 2.0)
```

---

## Avoid Artificial Utility Classes

Do not create classes that only wrap stateless helper functions with
`@staticmethod`.

Avoid this:

```python
class MathHelper:
    @staticmethod
    def add(a: int, b: int) -> int:
        return a + b
```

Prefer this:

```python
def add(a: int, b: int) -> int:
    return a + b
```

If grouping is needed, use a module:

```python
# math_ops.py

def add(a: int, b: int) -> int:
    return a + b
```

Avoid names like these unless there is a strong reason:

```python
class Utils: ...
class Helper: ...
class Manager: ...
class Processor: ...
class Handler: ...
```

These names are not forbidden, but they often indicate unclear
responsibility.

Prefer precise names that describe what the code owns, does, or represents.

Better examples:

```python
class HttpClient: ...
class FileReader: ...
class OrderBook: ...
class ImageDecoder: ...
class CommandParser: ...
class FrameRenderer: ...
```

---

## Resource Management

Use context managers for resources such as:

- Files
- Sockets
- Locks
- Database connections and transactions
- Temporary state that must be restored
- Any resource that must be released reliably

Resource acquisition and release should be tied to a `with` block, not to
manual `close()` calls scattered through the code.

Prefer standard library context managers where possible:

```text
open(...)
threading.Lock()
contextlib.suppress(...)
tempfile.TemporaryDirectory()
contextlib.closing(sqlite3.connect(...)) as conn, conn  # see below
```

Note that `with sqlite3.connect(...) as conn:` only commits or rolls back the
transaction; it does not close the connection. `contextlib.closing(...)` alone
closes without committing, so the writes are lost. Nest both:
`with closing(sqlite3.connect(path)) as conn, conn:`.

Avoid manual acquire/release in normal application code.

Prefer this:

```python
with open(path, "r", encoding="utf-8") as handle:
    contents = handle.read()
```

Avoid this:

```python
handle = open(path, "r", encoding="utf-8")
contents = handle.read()
handle.close()
```

Use `contextlib.contextmanager` or a custom `__enter__`/`__exit__` pair when
the standard library does not already provide an appropriate abstraction.

Example:

```python
from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def timer_state_restored(timer: "Timer") -> Iterator[None]:
    previous = timer.is_running
    try:
        yield
    finally:
        timer.is_running = previous
```

Or as a class when the resource has its own lifecycle:

```python
from typing import BinaryIO


class FileHandle:
    def __init__(self, path: str) -> None:
        self._path = path
        self._file: BinaryIO | None = None

    def __enter__(self) -> "FileHandle":
        self._file = open(self._path, "rb")
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self._file is not None:
            self._file.close()

    def read(self) -> bytes:
        assert self._file is not None
        return self._file.read()
```

Context-manager classes should clearly express ownership: entering acquires,
exiting releases, unconditionally.

---

## Inheritance, Protocols, and Polymorphism

Do not introduce inheritance just to organize code.

Use an abstract base class (`abc.ABC`) or `typing.Protocol` only when the
code truly needs interchangeable behavior behind a common interface.

Acceptable example (nominal typing, when subclasses must share more than a
method signature):

```python
from abc import ABC, abstractmethod
import math


class Shape(ABC):
    @abstractmethod
    def area(self) -> float: ...


class Circle(Shape):
    def __init__(self, radius: float) -> None:
        self._radius = radius

    def area(self) -> float:
        return math.pi * self._radius**2
```

Prefer `typing.Protocol` when callers only need structural compatibility and
should not be forced into an inheritance hierarchy:

```python
from collections.abc import Sequence
from typing import Protocol


class Renderable(Protocol):
    def render(self) -> str: ...


def render_all(items: Sequence[Renderable]) -> list[str]:
    return [item.render() for item in items]
```

Any object with a matching `render()` method satisfies `Renderable` without
inheriting from it — Python's duck typing makes structural typing the
lower-friction default (annotate parameters with `Sequence` or `Iterable`, not
`list`, which is invariant and would reject a `list[Circle]`); reach for `ABC` only when you need to force
subclasses to implement specific methods or share concrete base behavior.

Use this style when callers need to work with different concrete
implementations through the same interface:

```python
shapes: list[Shape] = [Circle(1.0), Circle(2.0)]
```

Avoid deep inheritance hierarchies unless there is a clear architectural
reason.

Before adding inheritance, consider these alternatives:

- Free functions
- `typing.Protocol` (structural typing)
- Composition
- `Enum` plus a dict of callables
- `functools.singledispatch`
- Strategy objects passed as plain callables
- Plain data (dataclasses) plus algorithms

Prefer composition over inheritance when behavior can be assembled from
smaller parts.

Avoid this style unless there is a strong reason:

```python
class Animal(ABC):
    @abstractmethod
    def speak(self) -> str: ...


class Dog(Animal): ...
class Cat(Animal): ...
class Bird(Animal): ...
```

A small number of cases may be better represented with a plain union type:

```python
import math
from dataclasses import dataclass


@dataclass
class Circle:
    radius: float


@dataclass
class Rectangle:
    width: float
    height: float


Shape = Circle | Rectangle


def area(shape: Shape) -> float:
    match shape:
        case Circle(radius=r):
            return math.pi * r**2
        case Rectangle(width=w, height=h):
            return w * h
```

A `match` over the union keeps each case's logic in one place. Because `area`
returns a value, mypy already reports a missing return when a case is not
handled. In a function that returns `None`, end the match with
`case _: typing.assert_never(shape)` (Python 3.11+, or `typing_extensions` on
3.10) to get the same check.

---

## Methods vs Free Functions

Prefer methods for operations that are part of the object's essential
behavior.

Good methods usually:

- Preserve invariants
- Mutate internal state intentionally
- Depend on private (`_`-prefixed) representation
- Represent core behavior of the abstraction

Prefer free functions for operations that are external algorithms.

Good free functions usually:

- Do not need private access
- Are broadly reusable
- Are easy to test independently
- Keep the type smaller
- Express a clear computation or transformation

Example:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Polygon:
    points: tuple["Point", ...]

    def __post_init__(self) -> None:
        if len(self.points) < 3:
            raise ValueError("a polygon needs at least three points")


def perimeter(polygon: Polygon) -> float:
    points = polygon.points
    total = 0.0

    for i, current in enumerate(points):
        next_point = points[(i + 1) % len(points)]
        total += distance(current, next_point)

    return total
```

In this example, `Polygon` protects the invariant that it has at least three
points: it is validated at construction and, being frozen with a tuple, cannot be
mutated afterwards. `perimeter` is a free function because it is an algorithm over the
public interface.

---

## Encapsulation Guidelines

Encapsulation should protect meaningful invariants, not create unnecessary
boilerplate.

Use a single leading underscore (`_balance`) and a `@property` when:

- The data must stay valid according to rules
- Changes must go through validation
- Representation may change later
- Ownership must be controlled

Public attributes are acceptable when:

- The type is simple passive data
- There are no invariants
- The fields are naturally part of the type's meaning
- The type is used as a value object or data-transfer object

Avoid writing trivial `@property` getters and setters just to imitate other
languages.

Prefer direct public fields for simple data:

```python
@dataclass
class Color:
    red: int
    green: int
    blue: int
```

Prefer validation when the values must be constrained:

```python
@dataclass(frozen=True)
class Color:
    red: int
    green: int
    blue: int

    def __post_init__(self) -> None:
        for name, value in (("red", self.red), ("green", self.green), ("blue", self.blue)):
            if not 0 <= value <= 255:
                raise ValueError(f"{name} must be between 0 and 255, got {value}")
```

Do not rely on name-mangled `__double_leading_underscore` attributes as an
access-control mechanism; a single underscore is Python's conventional
"non-public" signal and is sufficient for nearly all cases. Reserve double
underscores for avoiding real name collisions in a class hierarchy.

---

## State Management

Minimize mutable shared state.

Prefer:

- Local variables
- Function parameters
- Return values
- Immutable values (tuples, frozen dataclasses)
- Clear ownership
- Explicit dependencies

Avoid:

- Hidden module-level globals
- Singleton abuse
- Mutable default arguments
- Mutable global state
- Functions that secretly depend on external state

Avoid this:

```python
current_user = None  # module-level global


def can_access_document(document: "Document") -> bool:
    return document.owner == current_user
```

Prefer this:

```python
def can_access_document(document: "Document", user: "User") -> bool:
    return document.owner == user.id
```

Also avoid the classic mutable-default-argument pitfall, since default
values are evaluated once at function definition time:

```python
# Bug: the same list is shared and mutated across calls.
def add_item(item: str, items: list[str] = []) -> list[str]:
    items.append(item)
    return items
```

Prefer this:

```python
def add_item(item: str, items: list[str] | None = None) -> list[str]:
    if items is None:
        items = []
    return [*items, item]
```

Pass dependencies explicitly unless there is a strong reason not to.

---

## Error Handling

Use a clear error-handling strategy that is consistent with the surrounding
component and repository conventions.

Unlike Google-style C++, idiomatic Python uses exceptions as the default
error-handling mechanism, including for constructor failures. Raise a
specific exception type — never a bare `Exception` — for conditions that are
genuinely exceptional (invalid input, broken invariants, unreachable state).

Prefer "easier to ask forgiveness" (EAFP) over look-before-you-leap checks for
I/O: attempt the operation and let it raise. A `path.exists()` check before
opening races with other processes and duplicates the error `open()` already
raises. Keep `__init__` cheap and free of I/O; put loading in a factory
classmethod or a free function, so tests can build the object directly:

```python
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    timeout_seconds: int

    @classmethod
    def from_file(cls, path: Path) -> "Config":
        with path.open(encoding="utf-8") as handle:  # raises FileNotFoundError
            data = json.load(handle)
        return cls(timeout_seconds=int(data["timeout_seconds"]))
```

Prefer `None` or another sentinel return value — not exceptions — when absence
is a normal, expected outcome that every caller must handle (the `dict.get`
pattern). A return type of `X | None` makes that visible in the signature, while
an exception would be easy for callers to forget:

```python
def find_user_by_id(user_id: str) -> "User | None":
    ...
```

Use `bool` when callers only need success/failure and no diagnostic value
would be lost:

```python
def contains_user(user_id: str) -> bool:
    ...
```

Define a small custom exception hierarchy for a component's expected failure
modes instead of raising built-in exceptions for domain-specific errors:

```python
class OrderError(Exception):
    """Base class for order-processing failures."""


class InsufficientStockError(OrderError):
    def __init__(self, sku: str, requested: int, available: int) -> None:
        super().__init__(
            f"insufficient stock for {sku}: requested {requested}, available {available}"
        )
        self.sku = sku
        self.requested = requested
        self.available = available
```

Catch narrow, specific exception types. Avoid bare `except:` and avoid
broad `except Exception:` blocks that swallow errors silently:

```python
try:
    config = Config.from_file(path)
except FileNotFoundError:
    config = Config.from_file(default_path)
```

Avoid this:

```python
try:
    config = Config.from_file(path)
except Exception:
    pass
```

When a lower layer's exception crosses into your component's API, translate it
into the component's own exception type and chain it with `from`, so callers
catch one domain error while the traceback keeps the original cause:

```python
try:
    row = database.fetch_order(order_id)
except LookupError as err:
    raise OrderError(f"order {order_id} not found") from err
```

A broad `except Exception` is acceptable only at a top-level boundary (a request
handler, a CLI `main`, a worker loop) that logs the error with its traceback and
then fails the request or re-raises.

For failures that need rich diagnostics across process or API boundaries,
prefer the repository's established result/error type (e.g. a `Result`
dataclass or an error-response schema). Avoid mixing multiple error-handling
styles in the same component without a clear reason.

---

## Type Hints and Immutability

Use type hints on public function signatures and class attributes to
communicate intent to readers and static checkers. Unlike C++ `const`, they are
not enforced at runtime.

Prefer:

```python
def size(self) -> int:
    return self._size
```

Annotate parameters and return types on public APIs:

```python
def render(scene: "Scene") -> str: ...
```

Use `typing.Final` for module-level or class-level constants that must not
be reassigned:

```python
from typing import Final

MAX_RETRIES: Final = 3
```

Use immutable containers and `@dataclass(frozen=True)` when a value should
not change after construction:

```python
@dataclass(frozen=True)
class Point:
    x: float
    y: float
```

Prefer `tuple` over `list` for fixed-size, unchanging sequences returned from
a function, to signal to callers that the result should not be mutated.

Type hints and immutability together improve readability, correctness, and
API design, and let static checkers (`mypy`, `pyright`) catch mistakes before
runtime.

---

## Ownership and Reference Semantics

Python has no C++-style ownership model — every name is a reference to an
object, and assignment never copies. Make sharing and mutation explicit
instead.

Use plain values and container literals when ownership is simple:

```python
items: list["Item"] = []
```

Be explicit when a function receives a mutable object it does not own: avoid
mutating caller-supplied lists/dicts unless that mutation is the documented
contract, and prefer returning a new value instead.

```python
def with_item_added(items: list["Item"], item: "Item") -> list["Item"]:
    return [*items, item]
```

Use `copy.deepcopy` (or a dataclass's own copy pattern) only when a genuine
independent copy is required; deep copies are easy to reach for and easy to
overuse.

Pass collaborators as ordinary references; a constructor that stores an
injected dependency (a `Renderer` holding a `TextureCache`) does not need
`weakref`. The garbage collector frees reference cycles, so `weakref` is not
needed to avoid leaks either. Use it only when a reference must not decide the
target's lifetime: a back-reference from a child to its parent, or a cache or
registry that should drop entries once nothing else uses them
(`weakref.WeakValueDictionary`):

```python
import weakref


class TreeNode:
    def __init__(self, parent: "TreeNode | None" = None) -> None:
        self.children: list[TreeNode] = []
        self._parent = weakref.ref(parent) if parent is not None else None

    @property
    def parent(self) -> "TreeNode | None":
        return self._parent() if self._parent is not None else None
```

Document non-obvious lifetime or aliasing constraints in a docstring rather
than leaving callers to infer them from usage.

---

## Naming Guidance

Use names that describe the responsibility clearly.

Prefer nouns for types:

```python
class HttpClient: ...
class FileReader: ...
class OrderBook: ...


@dataclass
class Point: ...


@dataclass
class Size: ...
```

Prefer verbs or verb phrases for functions:

```python
def parse_config(): ...
def load_image(): ...
def calculate_total(): ...
def normalize_path(): ...
```

Avoid vague names:

```python
def do_stuff(): ...
def handle_data(): ...
def process(): ...
def run(): ...
def manage(): ...
```

Short names are acceptable for small scopes:

```python
for x in values:
    ...
```

Use more descriptive names for wider scopes, and follow PEP 8: `snake_case`
for functions and variables, `PascalCase` for classes, `UPPER_SNAKE_CASE`
for module-level constants.

---

## Module Organization

Keep modules focused.

A module should usually contain:

- One primary class or abstraction
- Closely related simple dataclasses
- Closely related free functions
- Implementation details prefixed with `_` when they are not part of the
  public API

Use packages (`__init__.py`) to group related functionality and control the
public surface: `__all__` defines what `from pkg import *` exports.

Example:

```python
# geometry/__init__.py
from .point import Point, distance
from .polygon import Polygon, perimeter

__all__ = ["Point", "distance", "Polygon", "perimeter"]
```

Avoid large modules that mix unrelated responsibilities.

Avoid catch-all modules such as:

```text
utils.py
helpers.py
misc.py
common.py
```

These are acceptable only for very small, clearly scoped collections.

---

## Testing Guidance

Prefer designs that are easy to test.

Free functions should be deterministic when possible.

Classes should expose behavior, not internal implementation details.

Avoid hidden dependencies that make tests fragile — the most common offender
in Python is reaching for `datetime.now()`, environment variables, or global
state directly inside business logic.

Prefer dependency injection over hard-coded global dependencies:

```python
class ReportGenerator:
    def __init__(self, clock: "Clock") -> None:
        self._clock = clock

    def generate(self) -> "Report":
        now = self._clock.now()
        ...
```

Avoid this:

```python
from datetime import datetime


class ReportGenerator:
    def generate(self) -> "Report":
        now = datetime.now()
        ...
```

When only one call needs the value, pass the value itself instead of a
collaborator. This is simpler than injecting a clock:

```python
from datetime import datetime


def is_expired(expires_at: datetime, now: datetime) -> bool:
    return now >= expires_at
```

Code should be designed so that core logic can be tested without file
systems, networks, timers, or global state when possible — favor plain
functions and constructor-injected collaborators over `unittest.mock`
patching of module internals.

---

## Generic Code

Use `TypeVar`/`Generic` or `typing.Protocol` when the algorithm naturally
works across multiple types.

Good example (the item type flows from the input to the output, which `Any`
would lose):

```python
from collections.abc import Callable, Hashable, Iterable
from typing import TypeVar

T = TypeVar("T")
K = TypeVar("K", bound=Hashable)


def group_by(items: Iterable[T], key: Callable[[T], K]) -> dict[K, list[T]]:
    groups: dict[K, list[T]] = {}
    for item in items:
        groups.setdefault(key(item), []).append(item)
    return groups
```

Do not write a generic helper for something the standard library already does
generically (`sum`, `max`, `functools.reduce`, `itertools`). On Python 3.12+ the
same function can be written `def group_by[T, K: Hashable](...)`.

Do not use generics or `Any` only to avoid writing clear types.

Do not over-generalize too early.

Prefer simple concrete code first. Introduce generics when repeated patterns
across multiple call sites are clear and the generic version remains
readable.

---

## Standard Library Preference

Prefer the Python standard library over custom implementations.

Use:

```text
dataclasses
collections (deque, defaultdict, Counter; typing.NamedTuple over namedtuple)
itertools
functools (lru_cache, singledispatch, reduce)
pathlib
contextlib
enum
typing
datetime
json
```

Do not write custom containers, path-handling utilities, string-formatting
helpers, or date/time utilities unless there is a strong project-specific
reason.

Prefer standard library and built-in idioms when they improve clarity:

```text
sorted(...)
any(...) / all(...)
enumerate(...)
zip(...)
list/dict/set comprehensions
```

Use comprehensions and built-ins when they make intent clearer. Use explicit
loops when they are more readable, especially with multiple side effects or
branches.

---

## Comments and Documentation

Write comments to explain why, not what.

Avoid comments that repeat the code:

```python
# Increment i by 1.
i += 1
```

Prefer comments that explain intent, constraints, or non-obvious decisions:

```python
# Keep this threshold in sync with the server-side timeout policy.
TIMEOUT_SECONDS = 30
```

Public functions and classes should have a docstring (PEP 257) that explains:

- What the function or type represents
- Argument and return semantics not obvious from type hints
- Exceptions raised
- Important preconditions
- Important postconditions

Example:

```python
def find_user_by_id(user_id: str) -> "User | None":
    """Look up a user by id.

    Returns None if no user with the given id exists. Raises
    ValueError if user_id is empty.
    """
```

Avoid excessive comments and docstrings around obvious code.

---

## Design Checklist

Before adding a new class, ask:

1. Does it own state?
2. Does it protect an invariant?
3. Does it manage a resource (does it need `__enter__`/`__exit__`)?
4. Does it represent a real concept?
5. Does it need polymorphic behavior?
6. Would a `@dataclass` plus free functions be clearer?

Before adding a new method, ask:

1. Does it need access to non-public state?
2. Does it preserve or modify an invariant?
3. Is it essential behavior of the object?
4. Would a free function be more flexible and testable?

Before adding a free function, ask:

1. Is this mostly an algorithm or calculation?
2. Does it avoid unnecessary access to non-public state?
3. Can it be tested independently?
4. Does it make the type simpler?

Before adding inheritance, ask:

1. Is runtime polymorphism required, or would structural typing
   (`typing.Protocol`) be enough?
2. Will callers use different implementations through a common interface?
3. Would composition be simpler?
4. Would a plain union type or `Enum` be clearer?
5. Is the hierarchy likely to remain shallow and stable?

---

## Anti-Patterns to Avoid (recap)

Each is illustrated with a good/bad pair in its own section above — this is a
scan list, not new content: excessive OOP (see When to Use Free Functions),
stateless utility classes (see Avoid Artificial Utility Classes), unnecessary
inheritance (see Inheritance, Protocols, and Polymorphism), global mutable
state and mutable default arguments (see State Management), broad
`except Exception: pass` blocks (see Error Handling), and classes with
unclear responsibility (see Naming Guidance).

---

## Summary Rule

As a default:

- Use `class` for state, ownership, lifetime, invariants, resource/context
  management, and true runtime polymorphism.
- Use `@dataclass` for simple passive data.
- Use free functions for algorithms, calculations, conversions, and
  procedural workflows.
- Avoid unnecessary inheritance; prefer `typing.Protocol` and composition.
- Avoid fake OOP such as stateless utility classes.
- Avoid hidden global mutable state and mutable default arguments.
- Raise specific exceptions for exceptional conditions and chain them with
  `from` at layer boundaries; use `None`/sentinel returns when absence is an
  expected outcome every caller must handle.
- Prefer explicit ownership and explicit dependencies.
- Prefer standard library facilities over custom infrastructure.
- Prefer simple, readable, testable, idiomatic Python.

When uncertain, choose the simpler design first. Add abstraction only when
the code clearly benefits from it.
