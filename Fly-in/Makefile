NAME = fly-in
PYTHON = python3
FILE = main.py models.py parser.py router.py visualizer.py window_config.py design/design_pattern.py design/__init__.py

all: $(NAME)

$(NAME):
	@echo "#!/bin/bash" > $(NAME)
	@echo "$(PYTHON) main.py \"\$$@\"" >> $(NAME)
	@chmod +x $(NAME)
	@echo "[+] Script de lancement '$(NAME)' créé avec succès."

install:
	$(PYTHON) -m pip install pygame flake8 mypy

run:
	$(PYTHON) main.py $(ARGS)

debug:
	$(PYTHON) -m pdb main.py $(ARGS)

lint:
	flake8 $(FILE)
	mypy --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs $(FILE)

lint-strict:
	flake8 $(FILE)
	mypy --strict $(FILE)

test: all
	@chmod +x run_tests.sh
	@./run_tests.sh

clean:
	@rm -rf __pycache__ */__pycache__ .mypy_cache temp_output.log
	@echo "rm -rf __pycache__ */__pycache__ .mypy_cache temp_output.log"
	@echo "[+] Fichiers de cache supprimés."

fclean: clean
	@rm -f $(NAME)
	@echo "rm -f $(NAME)"
	@echo "[+] Exécutable $(NAME) supprimé."

re: fclean all

.PHONY: all install run debug lint lint-strict test clean fclean re
