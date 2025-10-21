You can run the python test using the following:

/opt/homebrew/bin/uv run pytest [some_test::SomeClass] -v

And here is an example:

/opt/homebrew/bin/uv run pytest [tests/multilspy/test_runtime_dependency_models.py::TestInitializeParamsConfig] -v

Please note that we use uv and uv may not be on your path, so you have to run it using /opt/homebrew/bin/uv.
