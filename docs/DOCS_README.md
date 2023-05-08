# Notes on Auto-Generated Documentation 

Document directory structure:
```
ska-mid-dish-spfrx-talondx-console/
   docs/
      build
      src/
         index.rst
         diagrams/
            Engineering-Console-diagrams.vsdx
            engineering-console-context.png
            ...
         ...
         conf.py
      ...
  README.md
  Makefile
```

1. Run `make html` to generate the documentation.
1. `index.rst` references other `.rst` files in the `docs/src/` folder, which reference the Python code.
1. `autodoc_mock_imports` in `conf.py` may need to be updated when adding new imports in the Python code.
