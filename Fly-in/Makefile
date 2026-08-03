NAME = fly-in
PYTHON = python3

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
	flake8 .
	mypy --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs .

lint-strict:
	flake8 .
	mypy --strict .

test: all
	@chmod +x run_tests.sh
	@./run_tests.sh

clean:
	@rm -rf __pycache__ */__pycache__ .mypy_cache temp_output.log
	@echo "[+] Fichiers de cache supprimés."

fclean: clean
	@rm -f $(NAME)
	@echo "[+] Exécutable $(NAME) supprimé."

re: fclean all

.PHONY: all install run debug lint lint-strict test clean fclean re
