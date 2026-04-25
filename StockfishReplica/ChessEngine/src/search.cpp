#include "search.h"
#include "movegen.h"
#include "evaluate.h"
#include "tt.h"
#include <algorithm>
#include <iostream>
#include <sstream>
#include <cstring>

Searcher ENGINE;

// ── Time helpers ──────────────────────────────────────────────────────────────
long long Searcher::elapsed_ms() const {
    using namespace std::chrono;
    return duration_cast<milliseconds>(steady_clock::now() - start_time_).count();
}

bool Searcher::should_stop() const {
    if (stop_.load(std::memory_order_relaxed)) return true;
    if (limits_.infinite || limits_.ponder) return false;
    if (info_.nodes & 0xFFF) return false;
    return elapsed_ms() >= time_limit_ms_;
}

long long Searcher::alloc_time(Color stm) const {
    if (limits_.movetime > 0) return limits_.movetime - 20;
    int time  = (stm == WHITE) ? limits_.wtime : limits_.btime;
    int inc   = (stm == WHITE) ? limits_.winc  : limits_.binc;
    if (time == 0) return 5000;
    int mtg   = (limits_.movestogo > 0) ? limits_.movestogo : 25;
    long long allocated = time / mtg + inc / 2;
    allocated = std::min(allocated, (long long)(time - 50));
    return std::max(allocated, (long long)50);
}

// ── Move scoring helpers ──────────────────────────────────────────────────────
struct ScoredMove { Move move; int score; };

static int mvv_lva(PieceType attacker, PieceType victim) {
    return PIECE_VALUE[victim] * 10 - PIECE_VALUE[attacker];
}

// ── Quiescence search ─────────────────────────────────────────────────────────
Score Searcher::quiescence(Position &pos, Score alpha, Score beta, int ply) {
    if (should_stop()) return SCORE_ZERO;
    ++info_.nodes;
    info_.seldepth = std::max(info_.seldepth, ply);

    if (pos.is_draw()) return SCORE_DRAW;

    bool in_check = pos.in_check();
    Score stand_pat = SCORE_ZERO;

    if (!in_check) {
        stand_pat = evaluate(pos);
        if (stand_pat >= beta) return stand_pat;
        if (stand_pat > alpha) alpha = stand_pat;
    }

    MoveList ml;
    GenMode mode = in_check ? GEN_EVASIONS : GEN_CAPTURES;
    generate_moves(pos, ml, mode);

    ScoredMove smoves[256];
    int cnt = 0;
    for (int i = 0; i < ml.count; ++i) {
        Move m = ml.moves[i];
        if (!pos.is_legal(m)) continue;
        int sc = 0;
        Piece victim = pos.piece_on(to_sq(m));
        if (victim != NO_PIECE)
            sc = mvv_lva(type_of(pos.piece_on(from_sq(m))), type_of(victim));
        if (move_type(m) == MT_PROMO) sc += PIECE_VALUE[promo_type(m)];
        smoves[cnt++] = {m, sc};
    }
    std::sort(smoves, smoves + cnt, [](const ScoredMove &a, const ScoredMove &b){
        return a.score > b.score;
    });

    int moves_tried = 0;
    for (int i = 0; i < cnt; ++i) {
        Move m = smoves[i].move;

        // Delta pruning
        if (!in_check && move_type(m) != MT_PROMO) {
            Piece cap = pos.piece_on(to_sq(m));
            Score cap_val = (cap != NO_PIECE) ? PIECE_VALUE[type_of(cap)] : 0;
            if (stand_pat + cap_val + 200 < alpha) continue;
        }
        // SEE pruning
        if (!in_check && pos.see(m, 0) < 0) continue;

        StateInfo ns;
        pos.do_move(m, ns);
        Score score = -quiescence(pos, -beta, -alpha, ply + 1);
        pos.undo_move(m);

        if (score > alpha) {
            alpha = score;
            if (score >= beta) return score;
        }
        ++moves_tried;
    }

    if (in_check && moves_tried == 0) return mated_in(ply);
    return alpha;
}

// ── Alpha-beta ────────────────────────────────────────────────────────────────
Score Searcher::alpha_beta(Position &pos, Score alpha, Score beta, Depth depth,
                            int ply, bool is_pv, bool cut_node, Move prev_move)
{
    if (should_stop()) return SCORE_ZERO;

    const bool root = (ply == 0);
    if (depth <= 0) return quiescence(pos, alpha, beta, ply);

    ++info_.nodes;
    info_.seldepth = std::max(info_.seldepth, ply);

    alpha = std::max(alpha, mated_in(ply));
    beta  = std::min(beta,  mate_in(ply));
    if (alpha >= beta) return alpha;

    if (!root && pos.is_draw()) return SCORE_DRAW;
    if (ply >= MAX_PLY - 1) return evaluate(pos);

    bool tt_hit = false;
    TTEntry *tte = TT.probe(pos.hash(), tt_hit);
    Move tt_move = (tt_hit && tte->best_move) ? tte->best_move : NO_MOVE;
    Score tt_score = tt_hit ? TranspositionTable::score_from_tt(tte->score, ply) : SCORE_ZERO;

    if (!is_pv && tt_hit && tte->depth >= depth) {
        TTFlag f = tte->flag();
        if (f == TT_EXACT) return tt_score;
        if (f == TT_LOWER && tt_score >= beta)  return tt_score;
        if (f == TT_UPPER && tt_score <= alpha) return tt_score;
    }

    Score static_eval = (tt_hit && tte->static_eval != 0)
                      ? Score(tte->static_eval)
                      : evaluate(pos);

    bool in_check = pos.in_check();

    // ── Pruning (skip in check, PV, root) ────────────────────────────────────
    if (!in_check && !is_pv) {
        // Reverse futility
        if (depth <= 7 && static_eval - 70 * depth >= beta
            && std::abs(beta) < SCORE_MATE - 512)
            return static_eval;

        // Null move pruning
        if (depth >= 3 && static_eval >= beta
            && pos.plies_from_null() > 0
            && (pos.pieces(pos.side_to_move()) & ~pos.pieces(pos.side_to_move(), PAWN)
                                              & ~pos.pieces(pos.side_to_move(), KING)))
        {
            int R = 3 + depth / 4;
            StateInfo ns;
            pos.do_null_move(ns);
            Score null_sc = -alpha_beta(pos, -beta, -beta + 1, depth - R - 1,
                                         ply + 1, false, !cut_node, NO_MOVE);
            pos.undo_null_move();
            if (null_sc >= beta && std::abs(null_sc) < SCORE_MATE - 512)
                return null_sc;
        }

        // Futility pruning
        if (depth <= 2) {
            Score futility = static_eval + 100 + 150 * depth;
            if (futility <= alpha)
                return quiescence(pos, alpha, beta, ply);
        }
    }

    // ── Move generation ───────────────────────────────────────────────────────
    MoveList ml;
    generate_moves(pos, ml, in_check ? GEN_EVASIONS : GEN_ALL);

    struct SM { Move m; int sc; };
    SM smoves[256];
    int total = 0;
    Color us = pos.side_to_move();

    for (int i = 0; i < ml.count; ++i) {
        Move m = ml.moves[i];
        if (!pos.is_legal(m)) continue;

        int sc = 0;
        bool is_cap = pos.piece_on(to_sq(m)) != NO_PIECE || move_type(m) == MT_EP;

        if (m == tt_move) sc = 2000000;
        else if (is_cap || move_type(m) == MT_PROMO) {
            Piece victim = pos.piece_on(to_sq(m));
            PieceType pt_att = type_of(pos.piece_on(from_sq(m)));
            PieceType pt_vic = (victim != NO_PIECE) ? type_of(victim) : PAWN;
            int see_val = pos.see(m, 0);
            sc = (see_val >= 0) ? 1000000 + mvv_lva(pt_att, pt_vic)
                                : -1000   + mvv_lva(pt_att, pt_vic);
            if (move_type(m) == MT_PROMO) sc += PIECE_VALUE[promo_type(m)];
        } else if (m == tables_.killers[ply][0]) sc = 900000;
        else if (m == tables_.killers[ply][1]) sc = 800000;
        else if (ply >= 2 && prev_move != NO_MOVE
                 && tables_.counter_move[us][from_sq(prev_move)][to_sq(prev_move)] == m)
            sc = 700000;
        else
            sc = tables_.history[us][from_sq(m)][to_sq(m)];

        smoves[total++] = {m, sc};
    }

    // Insertion sort
    for (int i = 1; i < total; ++i) {
        SM key = smoves[i];
        int j = i - 1;
        while (j >= 0 && smoves[j].sc < key.sc) { smoves[j+1] = smoves[j]; --j; }
        smoves[j+1] = key;
    }

    if (total == 0) return in_check ? mated_in(ply) : SCORE_DRAW;

    Score best_score = -SCORE_INF;
    Move  best_move  = NO_MOVE;
    int   moves_tried = 0;
    bool  skip_quiets = false;

    for (int idx = 0; idx < total; ++idx) {
        Move m = smoves[idx].m;
        bool is_cap   = pos.piece_on(to_sq(m)) != NO_PIECE || move_type(m) == MT_EP;
        bool is_quiet = !is_cap && move_type(m) != MT_PROMO;

        if (skip_quiets && is_quiet) continue;

        // Late move pruning
        if (!root && !in_check && is_quiet && moves_tried >= 4 + depth * depth / 2
            && std::abs(alpha) < SCORE_MATE - 512)
            skip_quiets = true;

        // Bad capture pruning
        if (!root && !in_check && depth <= 8 && is_cap && moves_tried > 0
            && pos.see(m, 0) < 0)
            continue;

        StateInfo ns;
        pos.do_move(m, ns);

        Score score;
        Depth new_depth = depth - 1;
        if (pos.in_check()) ++new_depth;  // check extension

        if (moves_tried == 0) {
            score = -alpha_beta(pos, -beta, -alpha, new_depth, ply + 1, is_pv, false, m);
        } else {
            int reduction = 0;
            if (depth >= 3 && moves_tried >= 3 && is_quiet && !in_check) {
                reduction = 1 + (depth > 6 ? 1 : 0) + (moves_tried > 8 ? 1 : 0);
                if (!is_pv)   ++reduction;
                if (cut_node) ++reduction;
                reduction = std::max(0, std::min(reduction, new_depth - 1));
            }

            score = -alpha_beta(pos, -alpha - 1, -alpha, new_depth - reduction,
                                 ply + 1, false, true, m);
            if (reduction > 0 && score > alpha)
                score = -alpha_beta(pos, -alpha - 1, -alpha, new_depth,
                                     ply + 1, false, !cut_node, m);
            if (is_pv && score > alpha && score < beta)
                score = -alpha_beta(pos, -beta, -alpha, new_depth, ply + 1, true, false, m);
        }

        pos.undo_move(m);
        ++moves_tried;

        if (should_stop()) return SCORE_ZERO;

        if (score > best_score) {
            best_score = score;
            best_move  = m;
            if (root) root_best_move_ = m;

            if (score > alpha) {
                alpha = score;
                if (score >= beta) {
                    if (is_quiet) {
                        tables_.update_killers(m, ply);
                        int bonus = std::min(depth * depth, 512);
                        tables_.update_history(us, m, bonus);
                        for (int prev = 0; prev < idx; ++prev) {
                            Move pm = smoves[prev].m;
                            bool pm_quiet = pos.piece_on(to_sq(pm)) == NO_PIECE
                                         && move_type(pm) != MT_PROMO;
                            if (pm_quiet)
                                tables_.update_history(us, pm, -bonus / 2);
                        }
                        if (prev_move != NO_MOVE)
                            tables_.counter_move[us][from_sq(prev_move)][to_sq(prev_move)] = m;
                    }
                    TT.save(pos.hash(), best_score, static_eval, best_move, depth, TT_LOWER, ply);
                    return best_score;
                }
            }
        }
    }

    TTFlag flag = (best_score <= alpha) ? TT_UPPER : TT_EXACT;
    TT.save(pos.hash(), best_score, static_eval, best_move, depth, flag, ply);
    return best_score;
}

// ── PV extraction ─────────────────────────────────────────────────────────────
void Searcher::extract_pv(Position &pos, Move best, int depth, std::string &pv_str) {
    if (!best || depth == 0) return;
    LegalMoveList lml(pos);
    bool found = false;
    for (Move m : lml.list) if (m == best) { found = true; break; }
    if (!found) return;

    auto to_lan = [](Move m) -> std::string {
        std::string s;
        s += sq_name(from_sq(m));
        s += sq_name(to_sq(m));
        if (move_type(m) == MT_PROMO) {
            const char promo_chars[] = " nbrq";
            s += promo_chars[promo_type(m)];
        }
        return s;
    };

    pv_str += to_lan(best) + " ";

    StateInfo st;
    pos.do_move(best, st);
    bool hit;
    TTEntry *tte = TT.probe(pos.hash(), hit);
    Move next = (hit && tte->best_move) ? tte->best_move : NO_MOVE;
    extract_pv(pos, next, depth - 1, pv_str);
    pos.undo_move(best);
}

// ── Iterative deepening ───────────────────────────────────────────────────────
void Searcher::search(Position &pos, const SearchLimits &limits) {
    stop_.store(false);
    limits_    = limits;
    start_time_ = std::chrono::steady_clock::now();
    info_      = {};
    root_best_move_ = NO_MOVE;
    time_limit_ms_ = alloc_time(pos.side_to_move());

    tables_.clear();
    TT.new_search();

    Move  best_move  = NO_MOVE;
    Score best_score = SCORE_ZERO;
    int   max_depth  = limits.depth;

    auto move_to_str = [](Move m) -> std::string {
        std::string s;
        s += sq_name(from_sq(m));
        s += sq_name(to_sq(m));
        if (move_type(m) == MT_PROMO) {
            const char pc[] = " nbrq";
            s += pc[promo_type(m)];
        }
        return s;
    };

    for (int depth = 1; depth <= max_depth; ++depth) {
        info_.seldepth = depth;

        Score score;
        Score delta = 25;
        Score asp_alpha = (depth >= 4) ? std::max(-SCORE_INF, best_score - delta) : -SCORE_INF;
        Score asp_beta  = (depth >= 4) ? std::min( SCORE_INF, best_score + delta) :  SCORE_INF;

        while (true) {
            score = alpha_beta(pos, asp_alpha, asp_beta, depth, 0, true, false, NO_MOVE);
            if (should_stop()) break;

            if (score <= asp_alpha) {
                asp_alpha = std::max(asp_alpha - delta, -SCORE_INF);
                delta *= 2;
            } else if (score >= asp_beta) {
                asp_beta = std::min(asp_beta + delta, SCORE_INF);
                delta *= 2;
            } else break;
        }

        if (should_stop() && best_move != NO_MOVE) break;

        best_score = score;
        if (root_best_move_ != NO_MOVE) best_move = root_best_move_;

        long long ms = elapsed_ms();
        long long nps = (ms > 0) ? (info_.nodes * 1000 / ms) : info_.nodes * 1000;

        std::string pv_str;
        if (best_move != NO_MOVE) extract_pv(pos, best_move, depth, pv_str);

        std::string score_str;
        if (is_mate_score(best_score)) {
            int moves = (SCORE_MATE - std::abs(best_score) + 1) / 2;
            score_str = "mate " + std::to_string(best_score > 0 ? moves : -moves);
        } else {
            score_str = "cp " + std::to_string(best_score);
        }

        std::cout << "info depth " << depth
                  << " seldepth " << info_.seldepth
                  << " score " << score_str
                  << " nodes " << info_.nodes
                  << " nps " << nps
                  << " time " << ms
                  << " pv " << pv_str
                  << std::endl;

        if (!limits.infinite && !limits.ponder && ms >= time_limit_ms_ / 2) break;
    }

    std::cout << "bestmove " << (best_move != NO_MOVE ? move_to_str(best_move) : "0000")
              << std::endl;
}
