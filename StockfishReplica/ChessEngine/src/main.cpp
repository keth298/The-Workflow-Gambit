#include "bitboard.h"
#include "zobrist.h"
#include "uci.h"
#include <iostream>

int main(int argc, char *argv[]) {
    BB::init();
    Zobrist::init();

    // Optional: bench or direct command from CLI
    if (argc > 1 && std::string(argv[1]) == "bench") {
        // Quick bench: run a fixed position search
        std::string cmds[] = {
            "position startpos",
            "go depth 10"
        };
        for (auto &c : cmds) uci_handle(c);
        // Wait for search
        std::cin.ignore();
        return 0;
    }

    uci_loop();
    return 0;
}
