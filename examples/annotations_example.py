#!/usr/bin/env python3

### annotations_example.py
#   Copyright 2023 Nokia
###

"""Example showing manipulation of Annotations and Annotation classes."""

from pysros.wrappers import Annotation, Annotations, Leaf


def usage(command_name=None):
    """Return the usage information."""
    usage_string = (
        "Usage: %s username@host[:port]\n\nport is optional and will default to 830"  # pylint: disable=consider-using-f-string
        % command_name
    )
    return usage_string


def demo_index_functions(myleaf, one):
    """Demonstrates the use of index and index_annotation methods."""
    print("\n---- INDEX FUNCTIONS ----\n")
    print(
        "The index method takes an input and returns the location of the match.  This function "
        "must match exactly and completely, meaning in the case of annotation one "
        "the full one object must be used on input:",
        one,
    )
    print("")
    print(
        "Running index on the one annotation myleaf.annotations.index(one) or "
        "myleaf.annotations.index(Annotation(key='key1', data='value1')) provides the location"
        "of this annotation in the list of annotations:",
        myleaf.annotations.index(one),
    )
    print("")
    print(
        "The index_annotation method also returns the location of the annotation in the list, "
        "however this method accepts any combination the elements of the annotation: "
        "myleaf.annotations.index_annotation('key1'):",
        myleaf.annotations.index_annotation("key1"),
    )


def demo_get_functions(myleaf, one):
    """Demonstrates the use of get and get_annotation methods."""
    print("\n---- GET FUNCTIONS ----\n")
    print(
        "The get method takes an input and returns the annotation instance of the match.  "
        "This function must match exactly and completely, meaning in the case of "
        "annotation one the full one object must be used on input:",
        one,
    )
    print("")
    print(
        "Running get on the one annotation myleaf.annotations.get(one) or "
        "myleaf.annotations.get(Annotation(key='key1', data='value1')) provides the annotation"
        "instance of this annotation:",
        myleaf.annotations.get(one),
    )
    print("")
    print(
        "The get_annotation method also returns the annotation instance of the match, "
        "however this method accepts any combination the elements of the annotation: "
        "myleaf.annotations.get_annotation('key1'):",
        myleaf.annotations.get_annotation("key1"),
    )


def demo_remove_functions(myleaf, one):
    """Demonstrates the use of remove and remove_annotation methods."""
    print("\n---- REMOVE FUNCTIONS ----\n")
    print(
        "The remove method takes an input and removes the matching annotation instance "
        "from the list.  This function must match exactly and completely, meaning in the "
        "case of annotation one the full one object must be used on input:",
        one,
    )
    print("")
    print(
        "Running remove on the one annotation myleaf.annotations.delete(one) or "
        "myleaf.annotations.delete(Annotation(key='key1', data='value1')) removes the annotation"
        "instance from the list."
    )
    myleaf.annotations.remove(one)
    print("The contents of the list is now:", myleaf.annotations)
    print("")
    print(
        "The remove_annotation method also remoevs the annotation instance of the match, "
        "however this method accepts any combination the elements of the annotation: "
        "myleaf.annotations.remove_annotation('key2')."
    )
    myleaf.annotations.remove_annotation("key2")
    print("The contents of the list is now:", myleaf.annotations)


def demo_annotations():
    """Demonstrate the use of Annotation and Annotations classes in pySROS."""
    print(
        "This demonstration is not designed to configure the router with any of these "
        "annotations or to validate any of the input against any YANG schema. "
        "It is designed to demonstrate the data structures and the methods "
        "available to manipulate annotations."
    )
    print("\n---- INTRODUCTION ----\n")
    myleaf = Leaf("Example")
    print("Consider this leaf (called myleaf):", repr(myleaf))
    print("")
    print(
        "The annotations (YANG metadata) assigned to the leaf can be seen by issuing "
        "myleaf.annotations:",
        myleaf.annotations,
    )
    print("")
    print("Let's create two annotations to attach to this leaf:")
    print("  one = Annotation('key1', 'value1')")
    print("  two = Annotation('key2', 'value2')")
    one = Annotation("key1", "value1")
    two = Annotation("key2", "value2")
    print("")
    print("Assign these annotations to the leaf:")
    print("  myleaf.annotations = Annotations([one, two])")
    myleaf.annotations = Annotations([one, two])
    print("")
    print(
        "Looking again at the annotations on the leaf using myleaf.annotations:",
        myleaf.annotations,
    )
    print("")
    print(
        "The annotations attached to the leaf are treated as a list and therefore in addition to "
        "simply setting the values as above, standard list functions such as append also work:"
    )
    print("  three = Annotation('key3','value3')")
    three = Annotation("key3", "value3")
    print("  myleaf.annotations.append(three)")
    myleaf.annotations.append(three)
    print("")
    print(
        "Looking again at the annotations on the leaf using myleaf.annotations:",
        myleaf.annotations,
    )
    demo_index_functions(myleaf, one)
    demo_get_functions(myleaf, one)
    demo_remove_functions(myleaf, one)


def main():
    """Program starts from here."""
    demo_annotations()


if __name__ == "__main__":
    main()
