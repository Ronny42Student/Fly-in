#!/bin/bash

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

MAPS_DIR="maps"

echo -e "${CYAN}====================================================${NC}"
echo -e "${CYAN}    FLY-IN AUTOMATED TEST SUITE VALIDATION          ${NC}"
echo -e "${CYAN}====================================================${NC}"

run_test() {
    local category=$1
    local map_name=$2
    local expected=$3

    echo -e "\n[${category}] Test de la carte : ${YELLOW}${map_name}${NC}"

    if [ ! -f "${MAPS_DIR}/${map_name}" ]; then
        echo -e "  ${RED}❌ Fichier introuvable : ${map_name}${NC}"
        return
    fi

    ./fly-in "${MAPS_DIR}/${map_name}" > temp_output.log 2>&1

    if [ $? -eq 0 ]; then
        local turns=$(cat temp_output.log | wc -l)
        if [ -z "$turns" ]; then
            turns=0
        fi
        echo -e "  ${GREEN}✅ Succès !${NC} Simulation résolue en ${GREEN}${turns} tours${NC} (${expected})"
    else
        echo -e "  ${RED}❌ Échec de la simulation !${NC}"
        cat temp_output.log | grep -i "erreur" | sed 's/^/    /'
    fi
    rm -f temp_output.log
}

echo -e "\n${GREEN}--- 🟢 CATEGORIE: EASY ---${NC}"
run_test "EASY" "01_linear_path.txt" "Attendu: < 10 tours"
run_test "EASY" "02_simple_fork.txt" "Attendu: < 10 tours"
run_test "EASY" "03_basic_capacity.txt" "Attendu: < 10 tours"

echo -e "\n${YELLOW}--- 🟡 CATEGORIE: MEDIUM ---${NC}"
run_test "MEDIUM" "01_dead_end_trap.txt" "Attendu: 10-30 tours"
run_test "MEDIUM" "02_circular_loop.txt" "Attenov: 10-30 tours"
run_test "MEDIUM" "03_priority_puzzle.txt" "Attendu: 10-30 tours"

echo -e "\n${RED}--- 🔴 CATEGORIE: HARD ---${NC}"
run_test "HARD" "01_maze_nightmare.txt" "Attendu: 30+ tours"
run_test "HARD" "02_capacity_hell.txt" "Attendu: Spécifique timing"
run_test "HARD" "03_ultimate_challenge.txt" "Le test ultime complet"

echo -e "\n${NC}--- ⚫ CATEGORIE: CHALLENGER ---${NC}"
run_test "CHALLENGER" "01_the_impossible_dream.txt" "Record à battre: 41 tours"

echo -e "\n${CYAN}====================================================${NC}"
