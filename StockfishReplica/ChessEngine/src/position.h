#pragma once
#include "types.h"
#include <string>
#include <vector>
#include <cstring>  // memcpy

// ── State snapshot for unmake ─────────────────────────────────────────────────
struct StateInfo {
    u64           hash;
    Square        ep_sq;
    int           castling;
    int           fifty;
    int           plies_from_null;
    Piece         captured;
    // Precomputed check info (filled by do_move)
    Bitboard      checkers;
    Bitboard      pinned[2];        // [color] absolutely pinned pieces
    Bitboard      check_sq[6];      // squares from which a piece type gives check
    // Chain pointer — set by do_move, used by undo_move
    StateInfo    *previous = nullptr;
};

// ── Position ──────────────────────────────────────────────────────────────────
class Position {
public:
    Position() : state_(state_stack_) {}

    // Copy: snapshot bitboards + current state into state_stack_[0].
    // The history chain is NOT preserved (search doesn't need to undo past root).
    Position(const Position &o) { *this = o; }
    Position &operator=(const Position &o) {
        if (this == &o) return *this;
        // Copy piece data
        memcpy(occupancy_, o.occupancy_, sizeof(occupancy_));
        memcpy(by_type_,   o.by_type_,   sizeof(by_type_));
        memcpy(board_,     o.board_,     sizeof(board_));
        memcpy(king_sq_,   o.king_sq_,   sizeof(king_sq_));
        stm_      = o.stm_;
        game_ply_ = o.game_ply_;
        // Snapshot current state into our own stack slot 0
        state_stack_[0]          = *o.state_;
        state_stack_[0].previous = nullptr;  // detach chain from past
        state_ = &state_stack_[0];
        return *this;
    }

    void     set_fen(const std::string &fen);
    std::string fen() const;

    // ── Accessors ─────────────────────────────────────────────────────────────
    Bitboard pieces()                    const { return occupancy_[2]; }
    Bitboard pieces(Color c)             const { return occupancy_[c]; }
    Bitboard pieces(PieceType pt)        const { return by_type_[pt]; }
    Bitboard pieces(Color c, PieceType pt) const { return occupancy_[c] & by_type_[pt]; }
    Bitboard pieces(PieceType p1, PieceType p2) const { return by_type_[p1] | by_type_[p2]; }
    Bitboard pieces(Color c, PieceType p1, PieceType p2) const {
        return occupancy_[c] & (by_type_[p1] | by_type_[p2]);
    }

    Piece    piece_on(Square s) const { return board_[s]; }
    bool     empty(Square s)   const { return board_[s] == NO_PIECE; }
    Square   king_sq(Color c)  const { return king_sq_[c]; }
    Color    side_to_move()    const { return stm_; }
    Square   ep_sq()           const { return state_->ep_sq; }
    int      castling()        const { return state_->castling; }
    int      fifty_rule()      const { return state_->fifty; }
    int      plies_from_null() const { return state_->plies_from_null; }
    u64      hash()            const { return state_->hash; }
    Bitboard checkers()        const { return state_->checkers; }
    Bitboard pinned(Color c)   const { return state_->pinned[c]; }
    int      game_ply()        const { return game_ply_; }
    bool     in_check()        const { return state_->checkers != 0; }

    bool can_castle(int flag)  const { return (state_->castling & flag) != 0; }

    // ── Make / unmake ─────────────────────────────────────────────────────────
    void do_move  (Move m, StateInfo &new_state);
    void undo_move(Move m);                        // restores via StateInfo::previous
    void do_null_move  (StateInfo &ns);
    void undo_null_move();

    // ── Legality & check helpers ──────────────────────────────────────────────
    bool is_legal(Move m)    const;
    bool gives_check(Move m) const;
    Bitboard attackers_to(Square s, Bitboard occ) const;
    bool is_attacked(Square s, Color by) const;

    // ── Repetition / draw detection ───────────────────────────────────────────
    bool is_draw() const;

    // ── Static Exchange Evaluation ────────────────────────────────────────────
    int  see(Move m, int threshold = 0) const;

private:
    Bitboard occupancy_[3];    // [WHITE], [BLACK], [BOTH]
    Bitboard by_type_[6];      // by piece type
    Piece    board_[64];
    Square   king_sq_[2];
    Color    stm_;
    int      game_ply_;

    StateInfo  state_stack_[1024];
    StateInfo *state_ = state_stack_;

    void put_piece   (Piece p, Square s);
    void remove_piece(Square s);
    void move_piece  (Square from, Square to);
    void compute_check_info(StateInfo &st) const;
};
