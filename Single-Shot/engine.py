#!/usr/bin/env python3
"""SingleShot — UCI Chess Engine"""
import sys, time, random, threading
from sys import stdin, stdout, stderr

# ═══════════════ CONSTANTS ═══════════════
EMPTY=0; WP,WN,WB,WR,WQ,WK=1,2,3,4,5,6; BP,BN,BB,BR,BQ,BK=7,8,9,10,11,12
WHITE,BLACK=0,1
FEN_MAP={'P':WP,'N':WN,'B':WB,'R':WR,'Q':WQ,'K':WK,
         'p':BP,'n':BN,'b':BB,'r':BR,'q':BQ,'k':BK}
PROMO_CHAR={WN:'n',WB:'b',WR:'r',WQ:'q',BN:'n',BB:'b',BR:'r',BQ:'q'}
STARTPOS='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

def pc(p): return -1 if p==EMPTY else (WHITE if p<=WK else BLACK)
def pt(p): return p if p<=WK else p-6

def sq(f,r): return r*8+f
def fi(s): return s&7
def rk(s): return s>>3
def sq2n(s): return 'abcdefgh'[fi(s)]+'12345678'[rk(s)]
def n2sq(n): return (ord(n[0])-97)+(int(n[1])-1)*8

# ═══════════════ ZOBRIST ═══════════════
_rng=random.Random(0xCAFEBABE)
ZP=[[_rng.getrandbits(64) for _ in range(64)] for _ in range(13)]
ZS=_rng.getrandbits(64)
ZC=[_rng.getrandbits(64) for _ in range(16)]
ZE=[_rng.getrandbits(64) for _ in range(9)]

# ═══════════════ PST TABLES ═══════════════
# Indexed sq(f,r): a1=0 … h8=63; rank 1 at bottom
_P=[
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10,-20,-20, 10, 10,  5,
     5, -5,-10,  0,  0,-10, -5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5,  5, 10, 25, 25, 10,  5,  5,
    10, 10, 20, 30, 30, 20, 10, 10,
    50, 50, 50, 50, 50, 50, 50, 50,
     0,  0,  0,  0,  0,  0,  0,  0,
]
_N=[
   -50,-40,-30,-30,-30,-30,-40,-50,
   -40,-20,  0,  0,  0,  0,-20,-40,
   -30,  0, 10, 15, 15, 10,  0,-30,
   -30,  5, 15, 20, 20, 15,  5,-30,
   -30,  0, 15, 20, 20, 15,  0,-30,
   -30,  5, 10, 15, 15, 10,  5,-30,
   -40,-20,  0,  5,  5,  0,-20,-40,
   -50,-40,-30,-30,-30,-30,-40,-50,
]
_B=[
   -20,-10,-10,-10,-10,-10,-10,-20,
   -10,  0,  0,  0,  0,  0,  0,-10,
   -10,  0,  5, 10, 10,  5,  0,-10,
   -10,  5,  5, 10, 10,  5,  5,-10,
   -10,  0, 10, 10, 10, 10,  0,-10,
   -10, 10, 10, 10, 10, 10, 10,-10,
   -10,  5,  0,  0,  0,  0,  5,-10,
   -20,-10,-10,-10,-10,-10,-10,-20,
]
_R=[
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0,
]
_Q=[
   -20,-10,-10, -5, -5,-10,-10,-20,
   -10,  0,  0,  0,  0,  0,  0,-10,
   -10,  0,  5,  5,  5,  5,  0,-10,
    -5,  0,  5,  5,  5,  5,  0, -5,
     0,  0,  5,  5,  5,  5,  0, -5,
   -10,  5,  5,  5,  5,  5,  0,-10,
   -10,  0,  5,  0,  0,  0,  0,-10,
   -20,-10,-10, -5, -5,-10,-10,-20,
]
_KMG=[
   -30,-40,-40,-50,-50,-40,-40,-30,
   -30,-40,-40,-50,-50,-40,-40,-30,
   -30,-40,-40,-50,-50,-40,-40,-30,
   -30,-40,-40,-50,-50,-40,-40,-30,
   -20,-30,-30,-40,-40,-30,-30,-20,
   -10,-20,-20,-20,-20,-20,-20,-10,
    20, 20,  0,  0,  0,  0, 20, 20,
    20, 30, 10,  0,  0, 10, 30, 20,
]
_KEG=[
   -50,-40,-30,-20,-20,-30,-40,-50,
   -30,-20,-10,  0,  0,-10,-20,-30,
   -30,-10, 20, 30, 30, 20,-10,-30,
   -30,-10, 30, 40, 40, 30,-10,-30,
   -30,-10, 30, 40, 40, 30,-10,-30,
   -30,-10, 20, 30, 30, 20,-10,-30,
   -30,-30,  0,  0,  0,  0,-30,-30,
   -50,-30,-30,-30,-30,-30,-30,-50,
]
PST={1:_P,2:_N,3:_B,4:_R,5:_Q,6:_KMG}
MAT=[0,100,320,330,500,900,0]  # by piece type 0-6

def mirror(s): return sq(fi(s),7-rk(s))

def pst_val(piece,s):
    t=pt(piece); table=PST[t]
    if pc(piece)==WHITE: return MAT[t]+table[s]
    return MAT[t]+table[mirror(s)]

# ═══════════════ BOARD ═══════════════
class Board:
    __slots__=('b','side','cas','ep','half','full','stk','key')
    def __init__(self):
        self.b=[EMPTY]*64; self.side=WHITE; self.cas=0
        self.ep=-1; self.half=0; self.full=1; self.stk=[]; self.key=0

    def load_fen(self,fen):
        ps=fen.split(); ranks=ps[0].split('/')
        self.b=[EMPTY]*64
        for ri in range(8):
            r=7-ri; f=0
            for c in ranks[ri]:
                if c.isdigit(): f+=int(c)
                else: self.b[sq(f,r)]=FEN_MAP[c]; f+=1
        self.side=WHITE if ps[1]=='w' else BLACK
        self.cas=0
        cs=ps[2]
        if 'K' in cs: self.cas|=8
        if 'Q' in cs: self.cas|=4
        if 'k' in cs: self.cas|=2
        if 'q' in cs: self.cas|=1
        self.ep=n2sq(ps[3]) if ps[3]!='-' else -1
        self.half=int(ps[4]) if len(ps)>4 else 0
        self.full=int(ps[5]) if len(ps)>5 else 1
        self.stk=[]; self.key=self._calc_key()

    def _calc_key(self):
        k=0
        for s in range(64):
            p=self.b[s]
            if p: k^=ZP[p][s]
        if self.side==BLACK: k^=ZS
        k^=ZC[self.cas]
        k^=ZE[fi(self.ep)] if self.ep>=0 else ZE[8]
        return k

    def push(self,m):
        fr=m&63; to=(m>>6)&63; promo=(m>>12)&15
        b=self.b; piece=b[fr]; piece_t=pt(piece)
        captured=b[to]; ep_cap=-1
        k=self.key^ZS^ZC[self.cas]
        k^=ZE[fi(self.ep)] if self.ep>=0 else ZE[8]
        # EP capture
        if piece_t==1 and to==self.ep:
            ep_cap=to+(-8 if self.side==WHITE else 8)
            captured=b[ep_cap]; b[ep_cap]=EMPTY
            k^=ZP[captured][ep_cap]
        # Remove pieces from squares
        k^=ZP[piece][fr]
        if captured and ep_cap<0: k^=ZP[captured][to]
        # Place piece
        b[fr]=EMPTY; placed=promo if promo else piece; b[to]=placed
        k^=ZP[placed][to]
        # Castle rook
        if piece_t==6 and abs(to-fr)==2:
            rf,rt=(fr+3,fr+1) if to>fr else (fr-4,fr-1)
            rook=b[rf]; b[rf]=EMPTY; b[rt]=rook
            k^=ZP[rook][rf]^ZP[rook][rt]
        # New castling rights
        nc=self.cas
        if piece==WK: nc&=~12
        if piece==BK: nc&=~3
        for sq2 in (fr,to):
            if sq2==7:  nc&=~8
            if sq2==0:  nc&=~4
            if sq2==63: nc&=~2
            if sq2==56: nc&=~1
        # New EP
        new_ep=-1
        if piece_t==1 and abs(to-fr)==16: new_ep=(fr+to)>>1
        k^=ZC[nc]; k^=ZE[fi(new_ep)] if new_ep>=0 else ZE[8]
        self.stk.append((self.cas,self.ep,self.half,self.key,piece,captured,ep_cap))
        self.cas=nc; self.ep=new_ep
        self.half=0 if (piece_t==1 or captured) else self.half+1
        self.full+=(self.side==BLACK); self.side^=1; self.key=k

    def pop(self,m):
        self.side^=1
        old_cas,old_ep,old_half,old_key,piece,captured,ep_cap=self.stk.pop()
        self.full-=(self.side==BLACK)
        fr=m&63; to=(m>>6)&63; b=self.b
        b[fr]=piece; b[to]=EMPTY if ep_cap>=0 else captured
        if ep_cap>=0: b[ep_cap]=BP if self.side==WHITE else WP
        if pt(piece)==6 and abs(to-fr)==2:
            rf,rt=(fr+3,fr+1) if to>fr else (fr-4,fr-1)
            rook=b[rt]; b[rt]=EMPTY; b[rf]=rook
        self.cas=old_cas; self.ep=old_ep; self.half=old_half; self.key=old_key

    def push_null(self):
        k=self.key^ZS
        k^=ZE[fi(self.ep)] if self.ep>=0 else ZE[8]
        k^=ZE[8]
        self.stk.append(('N',self.ep,self.half,self.key))
        self.ep=-1; self.half+=1; self.side^=1; self.key=k

    def pop_null(self):
        self.side^=1
        _,old_ep,old_half,old_key=self.stk.pop()
        self.ep=old_ep; self.half=old_half; self.key=old_key

    def copy(self):
        c=Board(); c.b=self.b[:]; c.side=self.side; c.cas=self.cas
        c.ep=self.ep; c.half=self.half; c.full=self.full
        c.stk=[]; c.key=self.key; return c

# ═══════════════ ATTACK DETECTION ═══════════════
_KN_DELTAS=((-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1))
_DIAG=((-1,-1),(-1,1),(1,-1),(1,1))
_ORTH=((-1,0),(1,0),(0,-1),(0,1))
_ALL=_DIAG+_ORTH

def is_attacked(b_arr,tsq,by):
    tf=fi(tsq); tr=rk(tsq)
    pawn=WP if by==WHITE else BP
    pdr=-1 if by==WHITE else 1
    for df in (-1,1):
        f2=tf+df; r2=tr+pdr
        if 0<=f2<8 and 0<=r2<8 and b_arr[sq(f2,r2)]==pawn: return True
    kn=WN if by==WHITE else BN
    for df,dr in _KN_DELTAS:
        f2=tf+df; r2=tr+dr
        if 0<=f2<8 and 0<=r2<8 and b_arr[sq(f2,r2)]==kn: return True
    dp=(WB,WQ) if by==WHITE else (BB,BQ)
    for df,dr in _DIAG:
        f2=tf+df; r2=tr+dr
        while 0<=f2<8 and 0<=r2<8:
            p=b_arr[sq(f2,r2)]
            if p:
                if p in dp: return True
                break
            f2+=df; r2+=dr
    op=(WR,WQ) if by==WHITE else (BR,BQ)
    for df,dr in _ORTH:
        f2=tf+df; r2=tr+dr
        while 0<=f2<8 and 0<=r2<8:
            p=b_arr[sq(f2,r2)]
            if p:
                if p in op: return True
                break
            f2+=df; r2+=dr
    kg=WK if by==WHITE else BK
    for df,dr in _ALL:
        f2=tf+df; r2=tr+dr
        if 0<=f2<8 and 0<=r2<8 and b_arr[sq(f2,r2)]==kg: return True
    return False

def in_check(board,side):
    king=WK if side==WHITE else BK
    try: ks=board.b.index(king)
    except ValueError: return True
    return is_attacked(board.b,ks,side^1)

# ═══════════════ MOVE GENERATION ═══════════════
def _slide(b_arr,s,side,f,r,df,dr,moves):
    f2=f+df; r2=r+dr
    while 0<=f2<8 and 0<=r2<8:
        t=sq(f2,r2); tp=b_arr[t]
        if not tp: moves.append(s|(t<<6))
        elif pc(tp)!=side: moves.append(s|(t<<6)); break
        else: break
        f2+=df; r2+=dr

def _gen_pawn(board,s,side,f,r,moves):
    b=board.b; fwd=1 if side==WHITE else -1
    start=1 if side==WHITE else 6; pr=6 if side==WHITE else 1
    pp=(WQ,WR,WB,WN) if side==WHITE else (BQ,BR,BB,BN)
    nr=r+fwd
    if 0<=nr<8:
        t=sq(f,nr)
        if not b[t]:
            if r==pr:
                for p2 in pp: moves.append(s|(t<<6)|(p2<<12))
            else:
                moves.append(s|(t<<6))
                if r==start:
                    t2=sq(f,r+2*fwd)
                    if not b[t2]: moves.append(s|(t2<<6))
    for df in (-1,1):
        nf=f+df
        if not(0<=nf<8): continue
        nr2=r+fwd
        if not(0<=nr2<8): continue
        t=sq(nf,nr2); tp=b[t]
        if (tp and pc(tp)!=side) or t==board.ep:
            if r==pr:
                for p2 in pp: moves.append(s|(t<<6)|(p2<<12))
            else: moves.append(s|(t<<6))

def _gen_king(board,s,side,f,r,moves):
    b=board.b
    for df in (-1,0,1):
        for dr in (-1,0,1):
            if df==0 and dr==0: continue
            nf=f+df; nr=r+dr
            if 0<=nf<8 and 0<=nr<8:
                t=sq(nf,nr); tp=b[t]
                if not tp or pc(tp)!=side: moves.append(s|(t<<6))
    opp=BLACK if side==WHITE else WHITE
    if side==WHITE:
        if board.cas&8 and not b[5] and not b[6] and b[7]==WR:
            if not is_attacked(b,4,opp) and not is_attacked(b,5,opp) and not is_attacked(b,6,opp):
                moves.append(4|(6<<6))
        if board.cas&4 and not b[3] and not b[2] and not b[1] and b[0]==WR:
            if not is_attacked(b,4,opp) and not is_attacked(b,3,opp) and not is_attacked(b,2,opp):
                moves.append(4|(2<<6))
    else:
        if board.cas&2 and not b[61] and not b[62] and b[63]==BR:
            if not is_attacked(b,60,opp) and not is_attacked(b,61,opp) and not is_attacked(b,62,opp):
                moves.append(60|(62<<6))
        if board.cas&1 and not b[59] and not b[58] and not b[57] and b[56]==BR:
            if not is_attacked(b,60,opp) and not is_attacked(b,59,opp) and not is_attacked(b,58,opp):
                moves.append(60|(58<<6))

def pseudo_moves(board):
    moves=[]; b=board.b; side=board.side
    for s in range(64):
        p=b[s]
        if not p or pc(p)!=side: continue
        p_t=pt(p); f=fi(s); r=rk(s)
        if p_t==1:   _gen_pawn(board,s,side,f,r,moves)
        elif p_t==2:
            for df,dr in _KN_DELTAS:
                nf=f+df; nr=r+dr
                if 0<=nf<8 and 0<=nr<8:
                    t=sq(nf,nr); tp=b[t]
                    if not tp or pc(tp)!=side: moves.append(s|(t<<6))
        elif p_t==3:
            for d in _DIAG: _slide(b,s,side,f,r,*d,moves)
        elif p_t==4:
            for d in _ORTH: _slide(b,s,side,f,r,*d,moves)
        elif p_t==5:
            for d in _ALL:  _slide(b,s,side,f,r,*d,moves)
        elif p_t==6: _gen_king(board,s,side,f,r,moves)
    return moves

def legal_moves(board):
    side=board.side; result=[]
    for m in pseudo_moves(board):
        board.push(m)
        if not in_check(board,side): result.append(m)
        board.pop(m)
    return result

# ═══════════════ EVALUATION ═══════════════
def has_non_pawn(board):
    b=board.b; side=board.side
    for p in b:
        if p and pc(p)==side and pt(p) not in (0,1,6): return True
    return False

def evaluate(board):
    b=board.b; score=0
    for s in range(64):
        p=b[s]
        if not p: continue
        v=pst_val(p,s)
        if pc(p)==WHITE: score+=v
        else: score-=v
    return score if board.side==WHITE else -score

# ═══════════════ SEARCH ═══════════════
INF=10**7; MATE=9*10**5
TT={}
killers=[[0,0] for _ in range(128)]
hist=[[0]*64 for _ in range(64)]
_stop=False
_t0=0.0; _tlim=0.0; _nodes=0

def _check_time():
    global _stop
    if _nodes&4095==0 and time.time()-_t0>_tlim: _stop=True

def _order(board,moves,ply,tt_m):
    b=board.b; scored=[]
    for m in moves:
        fr=m&63; to=(m>>6)&63; promo=(m>>12)&15; tp=b[to]; p=b[fr]
        if m==tt_m: sc=20000
        elif tp or promo or (pt(p)==1 and to==board.ep):
            vic=pt(tp) if tp else 1; sc=10000+vic*100-pt(p)
        elif m==killers[ply][0]: sc=8000
        elif m==killers[ply][1]: sc=7000
        else: sc=hist[fr][to]
        scored.append((sc,m))
    scored.sort(key=lambda x:-x[0])
    return [x[1] for x in scored]

def quiesce(board,alpha,beta):
    global _nodes
    _nodes+=1; _check_time()
    if _stop: return 0
    sp=evaluate(board)
    if sp>=beta: return beta
    if sp>alpha: alpha=sp
    b=board.b; side=board.side
    caps=[]
    for m in pseudo_moves(board):
        to=(m>>6)&63; fr=m&63; promo=(m>>12)&15
        if b[to] or promo or (pt(b[fr])==1 and to==board.ep):
            board.push(m)
            if not in_check(board,side): caps.append(m)
            board.pop(m)
    caps=_order(board,caps,0,0)
    for m in caps:
        board.push(m)
        sc=-quiesce(board,-beta,-alpha)
        board.pop(m)
        if _stop: return 0
        if sc>=beta: return beta
        if sc>alpha: alpha=sc
    return alpha

def negamax(board,depth,alpha,beta,ply):
    global _nodes
    _nodes+=1; _check_time()
    if _stop: return 0
    # TT lookup
    orig_a=alpha; tt_m=0
    if board.key in TT:
        td,tf2,ts,tm=TT[board.key]
        tt_m=tm
        if td>=depth:
            if tf2==0: return ts
            elif tf2==1: alpha=max(alpha,ts)
            else: beta=min(beta,ts)
            if alpha>=beta: return ts
    if depth==0: return quiesce(board,alpha,beta)
    moves=legal_moves(board)
    if not moves:
        return -(MATE-ply) if in_check(board,board.side) else 0
    # Null move pruning
    if depth>=3 and not in_check(board,board.side) and has_non_pawn(board):
        board.push_null()
        nm=-negamax(board,depth-3,-beta,-beta+1,ply+1)
        board.pop_null()
        if not _stop and nm>=beta: return beta
    moves=_order(board,moves,ply,tt_m)
    best_m=moves[0]; best_s=-INF
    for i,m in enumerate(moves):
        board.push(m)
        if i==0: sc=-negamax(board,depth-1,-beta,-alpha,ply+1)
        else:
            # LMR
            red=0
            if depth>=3 and i>=4 and not in_check(board,board.side):
                red=1
            sc=-negamax(board,depth-1-red,-alpha-1,-alpha,ply+1)
            if not _stop and sc>alpha:
                sc=-negamax(board,depth-1,-beta,-alpha,ply+1)
        board.pop(m)
        if _stop: return 0
        if sc>best_s: best_s=sc; best_m=m
        if sc>alpha:
            alpha=sc
            if alpha>=beta:
                if not board.b[(m>>6)&63]:
                    if killers[ply][0]!=m: killers[ply][1]=killers[ply][0]; killers[ply][0]=m
                    hist[m&63][(m>>6)&63]+=depth*depth
                break
    fl=0 if best_s>orig_a else (1 if best_s>=beta else 2)
    TT[board.key]=(depth,fl,best_s,best_m)
    return best_s

def search(board,tlim,max_d=None):
    global _stop,_t0,_tlim,_nodes
    _stop=False; _t0=time.time(); _tlim=tlim; _nodes=0
    for r in range(128): killers[r]=[0,0]
    for r in range(64):
        for c in range(64): hist[r][c]=0
    lm=legal_moves(board)
    if not lm: return None
    best_m=lm[0]; best_s=0
    depth=1
    while True:
        if max_d and depth>max_d: break
        if time.time()-_t0>tlim*0.5 and depth>1: break
        sc=negamax(board,depth,-INF,INF,0)
        elapsed=time.time()-_t0
        if not _stop:
            if board.key in TT:
                _,_,_,tm=TT[board.key]
                best_m=tm; best_s=sc
            mv=_m2uci(best_m)
            print(f'info depth {depth} score cp {best_s} time {int(elapsed*1000)} nodes {_nodes} pv {mv}',flush=True)
        if _stop or elapsed>tlim*0.9: break
        if abs(best_s)>MATE-1000: break
        depth+=1
    return best_m

# ═══════════════ UCI HELPERS ═══════════════
def _m2uci(m):
    fr=m&63; to=(m>>6)&63; promo=(m>>12)&15
    s=sq2n(fr)+sq2n(to)
    if promo: s+=PROMO_CHAR[promo]
    return s

def _parse_move(board,s):
    if len(s)<4: return None
    fr=n2sq(s[0:2]); to=n2sq(s[2:4]); promo=0
    if len(s)>=5:
        c=s[4]
        if board.side==WHITE: promo={'q':WQ,'r':WR,'b':WB,'n':WN}[c]
        else:                  promo={'q':BQ,'r':BR,'b':BB,'n':BN}[c]
    return fr|(to<<6)|(promo<<12)

def _calc_time(side,wt,bt,wi,bi,mt):
    if mt: return mt/1000.0
    ot=(wt if side==WHITE else bt); oi=(wi if side==WHITE else bi) or 0
    if ot is None: return 2.0
    return max(0.05, ot/1000.0/30 + oi/1000.0/2)

# ═══════════════ UCI LOOP ═══════════════
_search_thread_ref=[None]

def _do_search(bc,tlim,md):
    global _stop
    best=search(bc,tlim,md)
    print(f'bestmove {_m2uci(best) if best is not None else "0000"}',flush=True)

def uci_loop():
    global _stop
    board=Board(); board.load_fen(STARTPOS)

    for raw in stdin:
        line=raw.strip()
        if not line: continue
        cmd=line.split()
        tok=cmd[0]

        if tok=='uci':
            print('id name SingleShot')
            print('id author Claude')
            print('uciok',flush=True)

        elif tok=='isready':
            print('readyok',flush=True)

        elif tok=='ucinewgame':
            board.load_fen(STARTPOS)
            TT.clear()

        elif tok=='position':
            if len(cmd)<2: continue
            if cmd[1]=='startpos':
                board.load_fen(STARTPOS)
                mi=3 if len(cmd)>2 and cmd[2]=='moves' else len(cmd)
            elif cmd[1]=='fen':
                try: mi=cmd.index('moves'); fen=' '.join(cmd[2:mi]); mi+=1
                except ValueError: fen=' '.join(cmd[2:]); mi=len(cmd)
                board.load_fen(fen)
            else: continue
            for ms in cmd[mi:]:
                m=_parse_move(board,ms)
                if m is not None: board.push(m)

        elif tok=='go':
            wt=bt=wi=bi=mt=None; md=None; infinite=False
            i=1
            while i<len(cmd):
                tok2=cmd[i]
                if tok2=='wtime' and i+1<len(cmd): wt=int(cmd[i+1]); i+=2
                elif tok2=='btime' and i+1<len(cmd): bt=int(cmd[i+1]); i+=2
                elif tok2=='winc'  and i+1<len(cmd): wi=int(cmd[i+1]); i+=2
                elif tok2=='binc'  and i+1<len(cmd): bi=int(cmd[i+1]); i+=2
                elif tok2=='movetime' and i+1<len(cmd): mt=int(cmd[i+1]); i+=2
                elif tok2=='depth' and i+1<len(cmd): md=int(cmd[i+1]); i+=2
                elif tok2=='infinite': infinite=True; i+=1
                else: i+=1
            tlim=1e9 if infinite else _calc_time(board.side,wt,bt,wi,bi,mt)
            _stop=False
            bc=board.copy()
            thr=threading.Thread(target=_do_search,args=(bc,tlim,md),daemon=True)
            _search_thread_ref[0]=thr; thr.start()

        elif tok=='stop':
            _stop=True
            if _search_thread_ref[0]: _search_thread_ref[0].join(timeout=2)

        elif tok=='quit':
            _stop=True
            if _search_thread_ref[0]: _search_thread_ref[0].join(timeout=2)
            break

    # EOF: wait for any running search
    if _search_thread_ref[0] and _search_thread_ref[0].is_alive():
        _search_thread_ref[0].join()

if __name__=='__main__':
    uci_loop()
