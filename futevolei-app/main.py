from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

app = FastAPI(title="Gerador de Torneios Futevôlei")

class BracketType(str, Enum):
    WINNERS = "WINNERS"
    LOSERS = "LOSERS"
    FINALS = "FINALS"

class Team(BaseModel):
    id: int
    name: str

class Match(BaseModel):
    id: int
    bracket: BracketType
    phase: int
    title: str
    team1_id: Optional[int] = None
    team2_id: Optional[int] = None
    score_team1: int = 0
    score_team2: int = 0
    winner_id: Optional[int] = None
    loser_id: Optional[int] = None
    winner_next_match_id: Optional[int] = None
    loser_next_match_id: Optional[int] = None
    winner_slot: int = 1
    loser_slot: int = 1

db_teams: List[Team] = []
db_matches: List[Match] = []

def get_team_name(team_id: Optional[int]) -> str:
    if team_id is None:
        return " — "
    team = next((t for t in db_teams if t.id == team_id), None)
    return team.name if team else " — "

@app.get("/", response_class=HTMLResponse)
def home_ui():
    teams_html = ""
    for t in db_teams:
        teams_html += f'''
        <li class="bg-slate-700 p-2 rounded mb-2 flex justify-between items-center text-sm border border-slate-600">
            <span class="font-bold text-gray-100">⚽ {t.name}</span>
            <div class="flex gap-1">
                <button onclick="editTeam({t.id}, '{t.name}')" class="bg-amber-500 text-slate-900 text-xs px-2 py-1 rounded hover:bg-amber-400 font-bold">✏️</button>
                <form action="/ui/delete-team" method="post" class="inline" onsubmit="return confirm('Remover dupla?');">
                    <input type="hidden" name="team_id" value="{t.id}">
                    <button type="submit" class="bg-red-500 text-white text-xs px-2 py-1 rounded hover:bg-red-600 font-bold">🗑️</button>
                </form>
            </div>
        </li>
        '''
    if not db_teams:
        teams_html = '<p class="text-gray-400 text-sm">Nenhuma dupla cadastrada.</p>'

    phases_winners = {}
    phases_losers = {}
    phases_finals = {}
    
    for m in db_matches:
        if m.bracket == BracketType.WINNERS:
            phases_winners.setdefault(m.phase, []).append(m)
        elif m.bracket == BracketType.LOSERS:
            phases_losers.setdefault(m.phase, []).append(m)
        elif m.bracket == BracketType.FINALS:
            phases_finals.setdefault(m.phase, []).append(m)

    def render_col(phase_num, matches, title):
        cards = ""
        for m in matches:
            t1 = get_team_name(m.team1_id)
            t2 = get_team_name(m.team2_id)
            ready = (m.team1_id is not None) and (m.team2_id is not None)
            disabled = "" if ready else "disabled"
            btn_class = "bg-amber-500 text-slate-900 hover:bg-amber-400 font-black" if ready else "bg-gray-300 text-gray-500 cursor-not-allowed"

            cards += f'''
            <div id="match-{m.id}" data-wnext="{m.winner_next_match_id or ''}" data-lnext="{m.loser_next_match_id or ''}" class="match-card bg-white border-2 border-gray-300 rounded-lg p-3 shadow-md w-64 my-3 flex-shrink-0 relative z-10">
                <div class="text-[10px] font-black text-gray-500 mb-1 flex justify-between uppercase">
                    <span>{m.title}</span>
                    <span>Jogo #{m.id}</span>
                </div>
                <form action="/ui/set-score" method="post" class="space-y-2">
                    <input type="hidden" name="match_id" value="{m.id}">
                    
                    <div class="flex justify-between items-center bg-gray-50 p-1.5 rounded border">
                        <span class="text-xs font-bold text-gray-800 truncate max-w-[130px]">{t1}</span>
                        <input type="number" name="score1" value="{m.score_team1}" {disabled} class="w-12 text-center border-2 border-amber-500 rounded font-black text-sm bg-amber-50 text-amber-900">
                    </div>

                    <div class="flex justify-between items-center bg-gray-50 p-1.5 rounded border">
                        <span class="text-xs font-bold text-gray-800 truncate max-w-[130px]">{t2}</span>
                        <input type="number" name="score2" value="{m.score_team2}" {disabled} class="w-12 text-center border-2 border-amber-500 rounded font-black text-sm bg-amber-50 text-amber-900">
                    </div>

                    <button type="submit" {disabled} class="w-full text-xs py-1 rounded transition {btn_class}">
                        { '💾 Salvar Placar' if ready else 'Aguardando Duplas' }
                    </button>
                </form>
            </div>
            '''
        return f'''
        <div class="flex-shrink-0 min-w-[270px]">
            <h3 class="text-xs font-extrabold text-amber-400 uppercase tracking-wider mb-2 text-center">{title}</h3>
            <div class="flex flex-col justify-around h-full">{cards}</div>
        </div>
        '''

    winners_cols = "".join([render_col(p, ms, f"Fase {p}" if p < 3 else "⚔️ Semi-Final") for p, ms in sorted(phases_winners.items())])
    losers_cols = "".join([render_col(p, ms, f"Perdedores Fase {p}") for p, ms in sorted(phases_losers.items())])
    finals_cols = "".join([render_col(p, ms, "🏆 Finais") for p, ms in sorted(phases_finals.items())])

    return f'''
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>Torneio Futevôlei - Com Linhas de Conexão</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            .bracket-container {{ position: relative; }}
            svg.lines-layer {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                pointer-events: none;
                z-index: 1;
            }}
        </style>
    </head>
    <body class="bg-slate-900 min-h-screen text-white font-sans flex flex-col">
        
        <header class="bg-slate-800 p-4 border-b border-slate-700 flex justify-between items-center shadow-lg z-20">
            <div class="flex items-center gap-3">
                <button onclick="toggleSidebar()" class="bg-slate-700 hover:bg-slate-600 text-amber-400 font-bold px-3 py-2 rounded-lg border border-slate-600 flex items-center gap-2 text-sm">
                    ⚙️ Duplas ({len(db_teams)})
                </button>
                <h1 class="text-xl font-black text-amber-400 hidden sm:block">🏐 Open Futevôlei</h1>
            </div>

            <form action="/ui/generate" method="post">
                <button type="submit" class="bg-amber-500 text-slate-900 px-5 py-2 rounded-lg font-black hover:bg-amber-400 shadow text-sm">⚡ Gerar / Montar Chaves</button>
            </form>
        </header>

        <div class="flex flex-1 relative overflow-hidden">
            
            <aside id="sidebar" class="bg-slate-800 border-r border-slate-700 w-80 p-4 flex-shrink-0 transition-all duration-300 z-30 overflow-y-auto">
                <div class="flex justify-between items-center mb-4">
                    <h2 class="font-bold text-md text-gray-200">Inscrição de Duplas</h2>
                    <button onclick="toggleSidebar()" class="text-gray-400 hover:text-white font-bold text-lg">✕</button>
                </div>

                <form id="teamForm" action="/ui/add-team" method="post" class="space-y-2 mb-4">
                    <input type="hidden" id="team_id" name="team_id" value="">
                    <input type="text" id="team_name" name="name" placeholder="Ex: Cayo e Levi" required class="w-full border p-2 rounded text-sm text-black">
                    <button type="submit" id="submitBtn" class="w-full bg-emerald-600 text-white p-2 rounded font-bold hover:bg-emerald-700 text-sm">+ Cadastrar Dupla</button>
                    <button type="button" id="cancelBtn" onclick="resetForm()" class="w-full bg-gray-500 text-white p-1 rounded font-bold text-xs hidden">Cancelar</button>
                </form>

                <h3 class="font-semibold text-xs text-gray-400 mb-2 uppercase">Inscritos ({len(db_teams)}):</h3>
                <ul class="max-h-96 overflow-y-auto">{teams_html}</ul>
            </aside>

            <main class="flex-1 overflow-x-auto p-6 space-y-8 bg-slate-950 bracket-container">
                <svg id="svg-lines" class="lines-layer"></svg>
                
                <!-- 1. CHAVE VENCEDORES -->
                <div>
                    <h2 class="text-xs font-black text-blue-400 uppercase tracking-widest mb-3">🔥 CHAVE DE VENCEDORES, SEMI-FINAIS & FINAIS</h2>
                    <div class="flex gap-12 overflow-x-auto pb-4 border-b border-slate-800">
                        {winners_cols + finals_cols or '<p class="text-gray-500 text-sm">Abra o menu de duplas, cadastre 8 duplas e clique em Gerar Chaves.</p>'}
                    </div>
                </div>

                <!-- 2. CHAVE PERDEDORES -->
                <div>
                    <h2 class="text-xs font-black text-red-400 uppercase tracking-widest mb-3">💀 CHAVE DE PERDEDORES (REPESCAGEM)</h2>
                    <div class="flex gap-12 overflow-x-auto pb-4">
                        {losers_cols or '<p class="text-gray-500 text-sm">Abra o menu de duplas, cadastre 8 duplas e clique em Gerar Chaves.</p>'}
                    </div>
                </div>

            </main>
        </div>

        <script>
            function toggleSidebar() {{
                document.getElementById('sidebar').classList.toggle('hidden');
            }}

            function editTeam(id, name) {{
                document.getElementById('team_id').value = id;
                document.getElementById('team_name').value = name;
                document.getElementById('teamForm').action = '/ui/edit-team';
                document.getElementById('submitBtn').innerText = '💾 Salvar Alteração';
                document.getElementById('submitBtn').className = 'w-full bg-amber-500 text-slate-900 p-2 rounded hover:bg-amber-400 text-sm';
                document.getElementById('cancelBtn').classList.remove('hidden');
            }}

            function resetForm() {{
                document.getElementById('team_id').value = '';
                document.getElementById('team_name').value = '';
                document.getElementById('teamForm').action = '/ui/add-team';
                document.getElementById('submitBtn').innerText = '+ Cadastrar Dupla';
                document.getElementById('cancelBtn').classList.add('hidden');
            }}

            function drawBracketLines() {{
                const svg = document.getElementById('svg-lines');
                const container = document.querySelector('.bracket-container');
                if (!svg || !container) return;

                svg.innerHTML = '';
                const containerRect = container.getBoundingClientRect();
                
                svg.setAttribute('width', container.scrollWidth);
                svg.setAttribute('height', container.scrollHeight);

                const cards = document.querySelectorAll('.match-card');
                
                cards.forEach(card => {{
                    const wNextId = card.getAttribute('data-wnext');
                    const lNextId = card.getAttribute('data-lnext');

                    if (wNextId) drawLineBetween(card, document.getElementById('match-' + wNextId), '#f59e0b', containerRect, svg);
                    if (lNextId) drawLineBetween(card, document.getElementById('match-' + lNextId), '#ef4444', containerRect, svg);
                }});
            }}

            function drawLineBetween(startEl, endEl, color, containerRect, svg) {{
                if (!startEl || !endEl) return;

                const r1 = startEl.getBoundingClientRect();
                const r2 = endEl.getBoundingClientRect();

                const x1 = r1.right - containerRect.left + document.querySelector('.bracket-container').scrollLeft;
                const y1 = r1.top + (r1.height / 2) - containerRect.top + document.querySelector('.bracket-container').scrollTop;

                const x2 = r2.left - containerRect.left + document.querySelector('.bracket-container').scrollLeft;
                const y2 = r2.top + (r2.height / 2) - containerRect.top + document.querySelector('.bracket-container').scrollTop;

                const midX = x1 + (x2 - x1) / 2;

                const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                const d = `M ${{x1}} ${{y1}} L ${{midX}} ${{y1}} L ${{midX}} ${{y2}} L ${{x2}} ${{y2}}`;
                
                path.setAttribute('d', d);
                path.setAttribute('stroke', color);
                path.setAttribute('stroke-width', '2');
                path.setAttribute('fill', 'none');
                path.setAttribute('opacity', '0.6');

                svg.appendChild(path);
            }}

            window.addEventListener('load', drawBracketLines);
            window.addEventListener('resize', drawBracketLines);
            document.querySelector('.bracket-container').addEventListener('scroll', drawBracketLines);
        </script>
    </body>
    </html>
    '''

@app.post("/ui/add-team")
def ui_add_team(name: str = Form(...)):
    new_id = len(db_teams) + 1
    db_teams.append(Team(id=new_id, name=name))
    return HTMLResponse('<script>window.location.href="/";</script>')

@app.post("/ui/edit-team")
def ui_edit_team(team_id: int = Form(...), name: str = Form(...)):
    team = next((t for t in db_teams if t.id == team_id), None)
    if team: team.name = name
    return HTMLResponse('<script>window.location.href="/";</script>')

@app.post("/ui/delete-team")
def ui_delete_team(team_id: int = Form(...)):
    global db_teams
    db_teams = [t for t in db_teams if t.id != team_id]
    return HTMLResponse('<script>window.location.href="/";</script>')

# --- CONEXÕES ATUALIZADAS ---
@app.post("/ui/generate")
def ui_generate():
    global db_matches
    db_matches.clear()
    
    total = len(db_teams)
    if total < 8:
        return HTMLResponse('<script>alert("Cadastre pelo menos 8 duplas!"); window.location.href="/";</script>')

    # 1. CHAVE DOS CAMPEÕES - FASE 1 (Perdedores vão para Repescagem Fase 1: Jogos 5 e 6)
    db_matches.append(Match(id=1, bracket=BracketType.WINNERS, phase=1, title="Jogo 1", team1_id=db_teams[0].id, team2_id=db_teams[1].id, winner_next_match_id=7, winner_slot=1, loser_next_match_id=5, loser_slot=1))
    db_matches.append(Match(id=2, bracket=BracketType.WINNERS, phase=1, title="Jogo 2", team1_id=db_teams[2].id, team2_id=db_teams[3].id, winner_next_match_id=7, winner_slot=2, loser_next_match_id=5, loser_slot=2))
    db_matches.append(Match(id=3, bracket=BracketType.WINNERS, phase=1, title="Jogo 3", team1_id=db_teams[4].id, team2_id=db_teams[5].id, winner_next_match_id=8, winner_slot=1, loser_next_match_id=6, loser_slot=1))
    db_matches.append(Match(id=4, bracket=BracketType.WINNERS, phase=1, title="Jogo 4", team1_id=db_teams[6].id, team2_id=db_teams[7].id, winner_next_match_id=8, winner_slot=2, loser_next_match_id=6, loser_slot=2))

    # 2. REPESCAGEM - FASE 1 (Perdedores da Fase 1 jogam entre si)
    # Vencedores avançam para a Repescagem Fase 2 (Jogos 9 e 10)
    db_matches.append(Match(id=5, bracket=BracketType.LOSERS, phase=1, title="Perdedores J1/J2", winner_next_match_id=9, winner_slot=2))
    db_matches.append(Match(id=6, bracket=BracketType.LOSERS, phase=1, title="Perdedores J3/J4", winner_next_match_id=10, winner_slot=2))

    # 3. CHAVE DOS CAMPEÕES - FASE 2
    # Vencedores vão pras Semis; Perdedores caem para a Repescagem Fase 2 (Jogos 9 e 10)
    db_matches.append(Match(id=7, bracket=BracketType.WINNERS, phase=2, title="Vencedores J1/J2", winner_next_match_id=11, winner_slot=1, loser_next_match_id=10, loser_slot=1))
    db_matches.append(Match(id=8, bracket=BracketType.WINNERS, phase=2, title="Vencedores J3/J4", winner_next_match_id=12, winner_slot=1, loser_next_match_id=9, loser_slot=1))

    # 4. REPESCAGEM - FASE 2 (Vencedor R-Fase1 vs Perdedor C-Fase2)
    # Vencedores vão para as Semis no Slot 2!
    db_matches.append(Match(id=9, bracket=BracketType.LOSERS, phase=2, title="Repescagem Fase 2 (A)", winner_next_match_id=11, winner_slot=2))
    db_matches.append(Match(id=10, bracket=BracketType.LOSERS, phase=2, title="Repescagem Fase 2 (B)", winner_next_match_id=12, winner_slot=2))

    # 5. SEMI-FINALS
    db_matches.append(Match(id=11, bracket=BracketType.WINNERS, phase=3, title="Semi-Final 1", winner_next_match_id=14, winner_slot=1, loser_next_match_id=13, loser_slot=1))
    db_matches.append(Match(id=12, bracket=BracketType.WINNERS, phase=3, title="Semi-Final 2", winner_next_match_id=14, winner_slot=2, loser_next_match_id=13, loser_slot=2))

    # 6. FINAIS
    db_matches.append(Match(id=13, bracket=BracketType.FINALS, phase=4, title="3º Lugar"))
    db_matches.append(Match(id=14, bracket=BracketType.FINALS, phase=4, title="🏆 Grande Final"))

    return HTMLResponse('<script>window.location.href="/";</script>')

@app.post("/ui/set-score")
def ui_set_score(match_id: int = Form(...), score1: int = Form(...), score2: int = Form(...)):
    match = next((m for m in db_matches if m.id == match_id), None)
    if match and match.team1_id is not None and match.team2_id is not None:
        match.score_team1 = score1
        match.score_team2 = score2

        if score1 > score2:
            match.winner_id, match.loser_id = match.team1_id, match.team2_id
        else:
            match.winner_id, match.loser_id = match.team2_id, match.team1_id

        # Mover Vencedor
        if match.winner_next_match_id:
            next_w = next((m for m in db_matches if m.id == match.winner_next_match_id), None)
            if next_w:
                if match.winner_slot == 1:
                    next_w.team1_id = match.winner_id
                else:
                    next_w.team2_id = match.winner_id

        # Mover Perdedor
        if match.loser_next_match_id:
            next_l = next((m for m in db_matches if m.id == match.loser_next_match_id), None)
            if next_l:
                if match.loser_slot == 1:
                    next_l.team1_id = match.loser_id
                else:
                    next_l.team2_id = match.loser_id

    return HTMLResponse('<script>window.location.href="/";</script>')