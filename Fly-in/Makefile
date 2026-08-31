NAME = fly-in
PYTHON = python3
FILE = main.py models.py parser.py router.py visualizer.py window_config.py design/design_pattern.py design/__init__.py
VENV = venv
BIN_VENV = $(VENV)/bin
DEFAULT_MAP = maps/01_linear_path.txt

all: $(NAME)

$(NAME):
	@echo "#!/bin/bash" > $(NAME)
	@echo "$(BIN_VENV)/$(PYTHON) main.py \"\$$@\"" >> $(NAME)
	@chmod +x $(NAME)
	@echo "[+] Script de lancement '$(NAME)' créé avec succès."

install:
	$(PYTHON) -m venv $(VENV)
	$(BIN_VENV)/$(PYTHON) -m pip install pygame flake8 mypy

run: all
	./$(NAME) $(DEFAULT_MAP) --visual

debug:
	$(BIN_VENV)/$(PYTHON) -m pdb main.py $(DEFAULT_MAP)

lint:
	$(BIN_VENV)/$(PYTHON) -m flake8 $(FILE)
	$(BIN_VENV)/$(PYTHON) -m mypy --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs $(FILE)

lint-strict:
	$(BIN_VENV)/$(PYTHON) -m flake8 $(FILE)
	$(BIN_VENV)/$(PYTHON) -m mypy --strict $(FILE)

test: all
	@chmod +x run_tests.sh
	@./run_tests.sh

clean:
	@rm -rf __pycache__ */__pycache__ .mypy_cache temp_output.log fly-in
	@echo "rm -rf __pycache__ */__pycache__ .mypy_cache temp_output.log fly-in"
	@echo "[+] Fichiers de cache supprimés."

fclean: clean
	@rm -rf $(VENV)
	@rm -f $(NAME)
	@echo "rm -rf $(VENV)"
	@echo "rm -f $(NAME)"
	@echo "[+] Environnement virtuel et exécutable $(NAME) supprimés."

re: fclean all

.PHONY: all install run debug lint lint-strict test clean fclean re
