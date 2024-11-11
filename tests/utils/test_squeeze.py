from dataclasses import dataclass

import pytest

from RosettaPy.utils.tools import squeeze


@dataclass
class Person:
    name: str
    age: int
    id_num: int


@dataclass(frozen=True)
class PersonHashable:
    name: str
    age: int
    id_num: int


def test_squeeze():
    p1 = Person("Alice", 25, 1)
    p2 = Person("Bob", 30, 2)
    p3 = Person("Alice", 25, 1)
    p4 = Person("Charlie", 35, 4)

    unsorted_list = [p1, p2, p3, p4]

    assert p1 == p3
    assert p1 is not p3

    with pytest.raises(TypeError, match="unhashable type: 'Person'"):
        # TypeError: unhashable type: 'Person'
        person_set = {p for p in unsorted_list}  # type: ignore

    squeezed_list = squeeze(unsorted_list)
    assert squeezed_list == [p1, p2, p4]


def test_squeeze_hashable():
    p1 = PersonHashable("Alice", 25, 1)
    p2 = PersonHashable("Bob", 30, 2)
    p3 = PersonHashable("Alice", 25, 1)
    p4 = PersonHashable("Charlie", 35, 4)

    unsorted_list = [p1, p2, p3, p4]
    assert p1 == p3
    assert p1 is not p3
    squeezed_list = squeeze(unsorted_list)
    assert squeezed_list == list({p1, p2, p4})

    person_set = {p for p in unsorted_list}
    assert len(person_set) == 3
    assert all(p in squeezed_list for p in person_set)


def test_squeeze_multiple_classes():
    p1 = PersonHashable("Alice", 30, 1)
    p2 = PersonHashable("Bob", 28, 2)
    p3 = Person("Charlie", 35, 3)

    with pytest.raises(ValueError, match="All items must be of the same dataclass. Found classes"):
        squeeze([p1, p2, p3])
