#include "uci.h"
#include "position.h"
#include "movegen.h"
#include "search.h"
#include "tt.h"
#include "bitboard.h"
#include "zobrist.h"
#include <iostream>
#include <sstream>
#include <thread>

static Position  g_pos;
static StateInfo g_state_stack[1024];
static std::thread g_search_thread;

static const char *START_FEN =
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

// ── Move string → Move ────────────────────────────────────────────────────────
static Move parse_move(const Position &pos, const std::string &s) {
    if (s.size() < 4) return NO_MOVE;
    int from_f = s[0] - 'a';
    int from_r = s[1] - '1';
    int to_f   = s[2] - 'a';
    int to_r   = s[3] - '1';
    if (from_f < 0 || from_f > 7 || from_r < 0 || from_r > 7 ||
        to_f   < 0 || to_f   > 7 || to_r   < 0 || to_r   > 7)
        return NO_MOVE;

    Square from = make_sq(from_f, from_r);
    Square to   = make_sq(to_f,   to_r);

    PieceType promo = NO_PIECE_TYPE;
    if (s.size() == 5) {
        switch (s[4]) {
            case 'n': promo = KNIGHT; break;
            case 'b': promo = BISHOP; break;
            case 'r': promo = ROOK;   break;
            case 'q': promo = QUEEN;  break;
        }
    }

    // Find the matching legal move
    LegalMoveList lml(pos);
    for (Move m : lml.list) {
        if (from_sq(m) != from || to_sq(m) != to) continue;
        if (promo != NO_PIECE_TYPE && move_type(m) == MT_PROMO && promo_type(m) != promo) continue;
        if (promo == NO_PIECE_TYPE && move_type(m) == MT_PROMO) continue;
        return m;
    }
    return NO_MOVE;
}

// ── Parse "position" command ──────────────────────────────────────────────────
static void parse_position(std::istringstream &ss) {
    std::string token;
    ss >> token;

    if (token == "startpos") {
        g_pos.set_fen(START_FEN);
        ss >> token;  // consume optional "moves"
    } else if (token == "fen") {
        std::string fen;
        while (ss >> token && token != "moves")
            fen += token + " ";
        if (!fen.empty()) fen.pop_back();  // trim trailing space
        g_pos.set_fen(fen);
    }

    // Apply move list using the position's own state_stack_
    // (set_fen puts state_ at state_stack_[0]; we chain from index 1 onward)
    if (token == "moves") {
        while (ss >> token) {
            Move m = parse_move(g_pos, token);
            if (m == NO_MOVE) break;
            g_pos.do_move(m, g_state_stack[g_pos.game_ply() & 1023]);
        }
    }
}

// ── Parse "go" command ────────────────────────────────────────────────────────
static void parse_go(std::istringstream &ss) {
    SearchLimits lim;
    std::string token;
    while (ss >> token) {
        if      (token == "depth")     ss >> lim.depth;
        else if (token == "movetime")  ss >> lim.movetime;
        else if (token == "wtime")     ss >> lim.wtime;
        else if (token == "btime")     ss >> lim.btime;
        else if (token == "winc")      ss >> lim.winc;
        else if (token == "binc")      ss >> lim.binc;
        else if (token == "movestogo") ss >> lim.movestogo;
        else if (token == "infinite")  lim.infinite = true;
        else if (token == "ponder")    lim.ponder   = true;
    }

    // Run search in a background thread
    if (g_search_thread.joinable()) g_search_thread.join();
    Position pos_copy = g_pos;   // snapshot for thread
    g_search_thread = std::thread([pos_copy, lim]() mutable {
        ENGINE.search(pos_copy, lim);
    });
}

// ── Main command handler ──────────────────────────────────────────────────────
void uci_handle(const std::string &line) {
    std::istringstream ss(line);
    std::string cmd;
    ss >> cmd;

    if (cmd == "uci") {
        std::cout << "id name HyperKnight\n"
                  << "id author Hyun\n"
                  << "option name Hash type spin default 64 min 1 max 4096\n"
                  << "option name Threads type spin default 1 min 1 max 1\n"
                  << "uciok\n";
    }
    else if (cmd == "isready") {
        std::cout << "readyok\n";
    }
    else if (cmd == "ucinewgame") {
        if (g_search_thread.joinable()) g_search_thread.join();
        ENGINE.reset();
        TT.clear();
        g_pos.set_fen(START_FEN);
    }
    else if (cmd == "position") {
        parse_position(ss);
    }
    else if (cmd == "go") {
        parse_go(ss);
    }
    else if (cmd == "stop") {
        ENGINE.stop();
        if (g_search_thread.joinable()) g_search_thread.join();
    }
    else if (cmd == "ponderhit") {
        // Treat like stop + continue – simplified: just stop
        ENGINE.stop();
    }
    else if (cmd == "setoption") {
        std::string name_tok, name, value_tok;
        ss >> name_tok >> name >> value_tok;
        std::string val;
        ss >> val;
        if (name == "Hash") {
            int mb = std::stoi(val);
            TT.resize(mb);
        }
    }
    else if (cmd == "quit") {
        ENGINE.stop();
        if (g_search_thread.joinable()) g_search_thread.join();
        std::exit(0);
    }
    else if (cmd == "d") {
        // Debug: print board
        std::cout << g_pos.fen() << "\n";
    }
}

void uci_loop() {
    std::string line;
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(nullptr);

    while (std::getline(std::cin, line)) {
        // Strip CR from Windows line endings
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (!line.empty()) uci_handle(line);
    }

    // EOF: stop search and clean up
    ENGINE.stop();
    if (g_search_thread.joinable()) g_search_thread.join();
}
