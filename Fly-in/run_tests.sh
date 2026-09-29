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

# Usage: run_test <category> <map file> <max turns target> <description>
# Targets come from the subject (VII.7 Performance Benchmarks).
run_test() {
    local category=$1
    local map_name=$2
    local target=$3
    local expected=$4

    echo -e "\n[${category}] Testing map: ${YELLOW}${map_name}${NC}"

    if [ ! -f "${MAPS_DIR}/${map_name}" ]; then
        echo -e "  ${RED}❌ File not found: ${map_name}${NC}"
        return
    fi

    # No --visual here: the pygame window would block the test suite.
    ./fly-in "${MAPS_DIR}/${map_name}" > temp_output.log 2>&1

    if [ $? -eq 0 ]; then
        local turns
        turns=$(wc -l < temp_output.log)
        if [ "$turns" -le "$target" ]; then
            echo -e "  ${GREEN}✅ Success!${NC} Solved in ${GREEN}${turns} turns${NC} (${expected})"
        else
            echo -e "  ${YELLOW}⚠️  Valid but above target:${NC} ${turns} turns (${expected})"
        fi
    else
        echo -e "  ${RED}❌ Simulation failed!${NC}"
        grep -i "error" temp_output.log | sed 's/^/    /'
    fi
    rm -f temp_output.log
}

echo -e "\n${GREEN}--- 🟢 CATEGORY: EASY ---${NC}"
run_test "EASY" "01_linear_path.txt" 6 "Target: <= 6 turns"
run_test "EASY" "02_simple_fork.txt" 8 "Target: <= 8 turns"
run_test "EASY" "03_basic_capacity.txt" 6 "Target: <= 6 turns"

echo -e "\n${YELLOW}--- 🟡 CATEGORY: MEDIUM ---${NC}"
run_test "MEDIUM" "01_dead_end_trap.txt" 12 "Target: <= 12 turns"
run_test "MEDIUM" "02_circular_loop.txt" 15 "Target: <= 15 turns"
run_test "MEDIUM" "03_priority_puzzle.txt" 12 "Target: <= 12 turns"

echo -e "\n${RED}--- 🔴 CATEGORY: HARD ---${NC}"
run_test "HARD" "01_maze_nightmare.txt" 30 "Target: <= 30 turns"
run_test "HARD" "02_capacity_hell.txt" 35 "Target: <= 35 turns"
run_test "HARD" "03_ultimate_challenge.txt" 45 "Target: <= 45 turns"

echo -e "\n${NC}--- ⚫ CATEGORY: CHALLENGER ---${NC}"
run_test "CHALLENGER" "01_the_impossible_dream.txt" 44 "Record to beat: 45 turns"

echo -e "\n${CYAN}====================================================${NC}"
