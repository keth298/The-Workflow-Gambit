#pragma once
#include <string>

// Runs the UCI command loop (blocking)
void uci_loop();

// Parse and handle a single UCI command line
void uci_handle(const std::string &line);
