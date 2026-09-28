"""JavaScript call / access references and global filtering."""

from src.tests.python_parser._assertions import (
    assert_reference_shape,
    assert_symbol_references_invariants,
    assert_symbols_invariants,
)


def test_js_references_fixture(javascript_parser, javascript_fixture_bytes):
    file_bytes = javascript_fixture_bytes("test_js_references.js")
    symbols, _imports, references = javascript_parser.parse(3, file_bytes)

    assert_symbols_invariants(symbols)
    assert_symbol_references_invariants(references)
    for r in references:
        assert_reference_shape(r, expected_file_id=3)

    kinds = {(r["ref_kind"], r["ref_symbol_name"]) for r in references}
    assert ("call", "myFunc") in kinds
    assert ("call", "helper") in kinds
    assert ("access", "obj.prop") in kinds
    assert ("call", "obj.meth") in kinds
    assert ("access", "maybe?.prop") in kinds
    assert ("call", "maybe?.meth") in kinds
    assert ("access", "arr[0]") in kinds

    assert not any(r["ref_symbol_name"].startswith("console.") for r in references)
    assert not any(r["ref_symbol_name"].startswith("Math.") for r in references)


def test_same_line_duplicate_calls_get_distinct_ids(
    javascript_parser, javascript_fixture_bytes
):
    file_bytes = javascript_fixture_bytes("same_line_duplicate_refs.js")
    symbols, _imports, references = javascript_parser.parse(55, file_bytes)

    assert_symbols_invariants(symbols)
    assert_symbol_references_invariants(references)
    for r in references:
        assert_reference_shape(r, expected_file_id=55)

    call_refs = [
        r
        for r in references
        if r["ref_kind"] == "call" and r["ref_symbol_name"] == "callee"
    ]
    assert len(call_refs) == 2
    assert call_refs[0]["source_line"] == call_refs[1]["source_line"]
    assert call_refs[0]["source_column"] != call_refs[1]["source_column"]
    assert call_refs[0]["id"] != call_refs[1]["id"]


def test_named_import_and_same_module_rewrite_ref_qn(
    javascript_parser, javascript_fixture_bytes
):
    file_bytes = javascript_fixture_bytes("ref_qn_imports.js")
    _, _, references = javascript_parser.parse(60, file_bytes, module_qn="pkg.sub.app")

    assert_symbol_references_invariants(references)
    named = next(r for r in references if r["ref_symbol_name"] == "renamed")
    assert named["ref_symbol_qualified_name"] == "pkg.sub.relative.mod.alpha"
    star = next(r for r in references if r["ref_symbol_name"] == "Star.go")
    assert star["ref_symbol_qualified_name"] == "pkg.lib.util.go"
    local = next(r for r in references if r["ref_symbol_name"] == "helper")
    assert local["ref_symbol_qualified_name"] == "pkg.sub.app.helper"


def test_directory_import_resolves_to_index_module(
    javascript_parser, javascript_fixture_bytes
):
    file_bytes = javascript_fixture_bytes("ref_qn_index_import.js")
    _, _, references = javascript_parser.parse(
        61, file_bytes, module_qn="components.app"
    )

    assert_symbol_references_invariants(references)
    button = next(r for r in references if r["ref_symbol_name"] == "Button")
    assert button["ref_symbol_qualified_name"] == "components.button.Button"
    card = next(r for r in references if r["ref_symbol_name"] == "Card")
    assert card["ref_symbol_qualified_name"] == "components.button.Card"


def test_relative_import_from_index_package_uses_directory_base(
    javascript_parser, javascript_fixture_bytes
):
    file_bytes = javascript_fixture_bytes("ref_qn_from_index.js")
    _, _, references = javascript_parser.parse(
        62, file_bytes, module_qn="components.button", is_package=True
    )

    assert_symbol_references_invariants(references)
    icon = next(r for r in references if r["ref_symbol_name"] == "Icon")
    assert icon["ref_symbol_qualified_name"] == "components.button.icon.Icon"
