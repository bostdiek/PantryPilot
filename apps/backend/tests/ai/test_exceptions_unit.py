from src.services.ai import exceptions


def test_exception_error_codes_and_messages():
    # Ensure each domain exception sets the correct error_code and message
    e = exceptions.HTMLFetchError()
    assert isinstance(e, exceptions.AIExtractionError)
    assert e.error_code == "fetch_failed"
    assert "Failed to fetch" in e.message

    e2 = exceptions.HTMLValidationError("no html")
    assert e2.error_code == "empty_html"
    assert e2.message == "no html"

    e3 = exceptions.AgentFailure()
    assert e3.error_code == "agent_error"

    e4 = exceptions.RecipeNotFound("nothing here")
    assert e4.error_code == "not_found"
    assert str(e4).startswith("not_found:")

    e5 = exceptions.ConversionError()
    assert e5.error_code == "convert_failed"
