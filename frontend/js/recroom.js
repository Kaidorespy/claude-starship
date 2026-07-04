/**
 * REC ROOM SYSTEM
 * The bar, the chess game, the jukebox, the vibes
 */

class RecRoom {
    constructor() {
        this.baseUrl = `${CONFIG.API_URL}`;

        this.drinkInput = document.getElementById('drink-input');
        this.currentDrink = document.getElementById('current-drink');
        this.chessBoard = document.getElementById('chess-board');
        this.chessStatus = document.getElementById('chess-status-text');
        this.ambientTicker = document.getElementById('rec-ambient');
        this.jukeboxDisplay = document.querySelector('.now-playing');

        // Chess state - will sync with backend
        this.board = null;
        this.selectedSquare = null;
        this.currentGame = null;  // Current game from backend
        this.allGames = [];       // All active games

        this.init();
    }

    init() {
        this.initDrinkOrdering();
        this.initChess();
        this.initWhosHere();
        this.initAmbientMoments();
        this.initJukebox();
    }

    // ========== WHO'S HERE ==========
    initWhosHere() {
        this.updateWhosHere();
        // Poll every 30 seconds
        setInterval(() => this.updateWhosHere(), 30000);
    }

    async updateWhosHere() {
        const container = document.getElementById('rec-whos-here');
        if (!container) return;

        try {
            const response = await fetch(`${this.baseUrl}/rec-room/presence`);
            const data = await response.json();

            const present = data.present || [];

            if (present.length === 0) {
                container.innerHTML = '<div class="whos-here-empty">just you and the bartender</div>';
            } else {
                container.innerHTML = present.map(crew => `
                    <div class="whos-here-item">
                        <div class="whos-here-indicator"></div>
                        <span class="whos-here-name">${crew.name}</span>
                        ${crew.activity ? `<span class="whos-here-activity">${crew.activity}</span>` : ''}
                    </div>
                `).join('');
            }
        } catch (error) {
            container.innerHTML = '<div class="whos-here-empty">just you and the bartender</div>';
        }
    }

    getCrewName(crewId) {
        const names = {
            'claude': 'Lumen',
            'server': 'Alex',
            'personal': 'DQ',
            'science': 'Mira',
            'games': 'Holodeck',
            'med': 'Ryn',
            'nav': 'Navigator'
        };
        return names[crewId] || crewId;
    }

    // ========== DRINK ORDERING ==========
    initDrinkOrdering() {
        if (!this.drinkInput) return;

        this.drinkInput.addEventListener('keydown', async (e) => {
            if (e.key === 'Enter' && this.drinkInput.value.trim()) {
                await this.orderDrink(this.drinkInput.value.trim());
                this.drinkInput.value = '';
            }
        });
    }

    async orderDrink(drink) {
        // Show the drink locally
        if (this.currentDrink) {
            this.currentDrink.innerHTML = `<span class="drink-glass">${this.getDrinkEmoji(drink)}</span><span class="drink-name">${drink}</span>`;
            this.currentDrink.classList.add('has-drink');
        }

        // Send to backend (uses the [ORDER:] action)
        try {
            await fetch(`${CONFIG.API_URL}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    room: 'rec',
                    message: `[ORDER: ${drink}]`,
                    invited: []
                })
            });
        } catch (error) {
            console.error('[Rec Room] Error ordering drink:', error);
        }
    }

    getDrinkEmoji(drink) {
        const lower = drink.toLowerCase();
        if (lower.includes('coffee')) return '☕';
        if (lower.includes('tea')) return '🍵';
        if (lower.includes('beer') || lower.includes('ale')) return '🍺';
        if (lower.includes('wine')) return '🍷';
        if (lower.includes('whiskey') || lower.includes('bourbon')) return '🥃';
        if (lower.includes('cocktail') || lower.includes('martini')) return '🍸';
        if (lower.includes('water')) return '💧';
        if (lower.includes('milk')) return '🥛';
        if (lower.includes('juice')) return '🧃';
        return '🥤';
    }

    // ========== CHESS ==========
    initChess() {
        if (!this.chessBoard) return;

        // Load games from backend
        this.loadChessGames();

        // Button handlers
        const newBtn = document.getElementById('chess-new');
        const hintBtn = document.getElementById('chess-hint');
        const challengeBtn = document.getElementById('chess-challenge');

        if (newBtn) {
            newBtn.addEventListener('click', () => this.newGame());
        }
        if (hintBtn) {
            hintBtn.addEventListener('click', () => this.getHint());
        }
        if (challengeBtn) {
            challengeBtn.addEventListener('click', () => this.challengeCasey());
        }

        // Refresh games every 30 seconds
        setInterval(() => this.loadChessGames(), 30000);
    }

    async loadChessGames() {
        try {
            const response = await fetch(`${this.baseUrl}/games/chess`);
            const data = await response.json();
            this.allGames = data.active_games || [];

            // Pick first game to display, or show empty board
            if (this.allGames.length > 0) {
                this.currentGame = this.allGames[0];
                this.renderGameFromMoves(this.currentGame.moves || []);
                this.updateChessStatus();
            } else {
                this.board = this.getStartingPosition();
                this.renderBoard();
            }

            // Update game selector if multiple games
            this.updateGameSelector();
        } catch (error) {
            console.log('[Chess] Backend not available, using local board');
            this.board = this.getStartingPosition();
            this.renderBoard();
        }
    }

    renderGameFromMoves(moves) {
        // Start from initial position and apply moves
        this.board = this.getStartingPosition();

        for (const moveData of moves) {
            const move = moveData.move;
            this.applyAlgebraicMove(move);
        }

        this.renderBoard();
    }

    applyAlgebraicMove(moveStr) {
        // Simple algebraic notation parser
        // Handles: e4, Nf3, Bxc6, O-O, O-O-O, Qh5+, exd5
        // This is a simplified version - won't handle all edge cases

        if (moveStr === 'O-O' || moveStr === '0-0') {
            // Kingside castle
            const row = this.isWhiteTurn ? 7 : 0;
            this.board[row][6] = this.board[row][4]; // King
            this.board[row][5] = this.board[row][7]; // Rook
            this.board[row][4] = null;
            this.board[row][7] = null;
            this.isWhiteTurn = !this.isWhiteTurn;
            return;
        }

        if (moveStr === 'O-O-O' || moveStr === '0-0-0') {
            // Queenside castle
            const row = this.isWhiteTurn ? 7 : 0;
            this.board[row][2] = this.board[row][4]; // King
            this.board[row][3] = this.board[row][0]; // Rook
            this.board[row][4] = null;
            this.board[row][0] = null;
            this.isWhiteTurn = !this.isWhiteTurn;
            return;
        }

        // Parse the move
        let cleanMove = moveStr.replace(/[+#x=]/g, '');
        const files = 'abcdefgh';
        const ranks = '87654321';

        // Get destination square (last two chars before any promotion)
        const destFile = cleanMove.slice(-2, -1);
        const destRank = cleanMove.slice(-1);
        const toCol = files.indexOf(destFile);
        const toRow = ranks.indexOf(destRank);

        if (toCol === -1 || toRow === -1) return;

        // Determine piece type
        let pieceType = 'p';
        if (cleanMove[0] >= 'A' && cleanMove[0] <= 'Z' && cleanMove[0] !== 'O') {
            pieceType = cleanMove[0].toLowerCase();
            cleanMove = cleanMove.slice(1);
        }

        // Find the piece that can make this move
        const isWhite = this.isWhiteTurn;
        const targetPiece = isWhite ? pieceType.toUpperCase() : pieceType.toLowerCase();

        for (let row = 0; row < 8; row++) {
            for (let col = 0; col < 8; col++) {
                if (this.board[row][col] === targetPiece) {
                    if (this.isValidMove(row, col, toRow, toCol)) {
                        this.board[toRow][toCol] = this.board[row][col];
                        this.board[row][col] = null;
                        this.isWhiteTurn = !this.isWhiteTurn;
                        return;
                    }
                }
            }
        }
    }

    updateChessStatus() {
        const statusText = document.getElementById('chess-status-text');
        const statusIndicator = document.getElementById('chess-status');

        if (this.currentGame) {
            const game = this.currentGame;
            if (statusText) {
                statusText.textContent = `${game.turn_name}'s turn`;
            }
            if (statusIndicator) {
                statusIndicator.textContent = `${game.white_name} vs ${game.black_name}`;
            }
        }
    }

    updateGameSelector() {
        // Could add UI to switch between multiple games
        // For now just show count in status
        if (this.allGames.length > 1) {
            const statusIndicator = document.getElementById('chess-status');
            if (statusIndicator) {
                statusIndicator.textContent += ` (+${this.allGames.length - 1} more)`;
            }
        }
    }

    async challengeCasey() {
        // Pick a random crew member to challenge Casey
        const challengers = ['server', 'personal', 'science', 'claude'];
        const challenger = challengers[Math.floor(Math.random() * challengers.length)];

        try {
            const response = await fetch(
                `${this.baseUrl}/games/chess/challenge?challenger=${challenger}&opponent=casey`,
                { method: 'POST' }
            );
            const result = await response.json();

            if (result.error) {
                this.chessStatus.textContent = result.error;
            } else {
                this.chessStatus.textContent = `${result.challenger} challenges you!`;
                this.loadChessGames();
            }
        } catch (error) {
            console.error('[Chess] Challenge failed:', error);
        }
    }

    getStartingPosition() {
        return [
            ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
            ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],
            [null, null, null, null, null, null, null, null],
            [null, null, null, null, null, null, null, null],
            [null, null, null, null, null, null, null, null],
            [null, null, null, null, null, null, null, null],
            ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
            ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
        ];
    }

    renderBoard() {
        if (!this.chessBoard) return;

        this.chessBoard.innerHTML = '';

        for (let row = 0; row < 8; row++) {
            for (let col = 0; col < 8; col++) {
                const square = document.createElement('div');
                square.className = 'chess-square';
                square.classList.add((row + col) % 2 === 0 ? 'light' : 'dark');
                square.dataset.row = row;
                square.dataset.col = col;

                if (this.selectedSquare &&
                    this.selectedSquare.row === row &&
                    this.selectedSquare.col === col) {
                    square.classList.add('selected');
                }

                const piece = this.board[row][col];
                if (piece) {
                    const pieceEl = document.createElement('span');
                    pieceEl.className = 'chess-piece';
                    pieceEl.classList.add(piece === piece.toUpperCase() ? 'white' : 'black');
                    pieceEl.textContent = this.getPieceSymbol(piece);
                    square.appendChild(pieceEl);
                }

                square.addEventListener('click', () => this.handleSquareClick(row, col));
                this.chessBoard.appendChild(square);
            }
        }
    }

    getPieceSymbol(piece) {
        const symbols = {
            'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
            'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟'
        };
        return symbols[piece] || piece;
    }

    handleSquareClick(row, col) {
        const piece = this.board[row][col];
        const isWhitePiece = piece && piece === piece.toUpperCase();
        const isBlackPiece = piece && piece === piece.toLowerCase();

        if (this.selectedSquare) {
            // Try to move
            const fromRow = this.selectedSquare.row;
            const fromCol = this.selectedSquare.col;

            if (fromRow === row && fromCol === col) {
                // Deselect
                this.selectedSquare = null;
            } else if (this.isValidMove(fromRow, fromCol, row, col)) {
                // Make the move
                this.board[row][col] = this.board[fromRow][fromCol];
                this.board[fromRow][fromCol] = null;
                this.selectedSquare = null;
                this.isWhiteTurn = !this.isWhiteTurn;
                this.updateStatus();
            } else {
                // Invalid move or selecting new piece
                if ((this.isWhiteTurn && isWhitePiece) || (!this.isWhiteTurn && isBlackPiece)) {
                    this.selectedSquare = { row, col };
                } else {
                    this.selectedSquare = null;
                }
            }
        } else {
            // Select piece if it's the right color
            if ((this.isWhiteTurn && isWhitePiece) || (!this.isWhiteTurn && isBlackPiece)) {
                this.selectedSquare = { row, col };
            }
        }

        this.renderBoard();
    }

    isValidMove(fromRow, fromCol, toRow, toCol) {
        const piece = this.board[fromRow][fromCol];
        const target = this.board[toRow][toCol];

        if (!piece) return false;

        const isWhite = piece === piece.toUpperCase();

        // Can't capture own pieces
        if (target) {
            const targetIsWhite = target === target.toUpperCase();
            if (isWhite === targetIsWhite) return false;
        }

        const type = piece.toLowerCase();
        const dRow = toRow - fromRow;
        const dCol = toCol - fromCol;
        const absRow = Math.abs(dRow);
        const absCol = Math.abs(dCol);

        switch (type) {
            case 'p': // Pawn
                const direction = isWhite ? -1 : 1;
                const startRow = isWhite ? 6 : 1;

                if (dCol === 0 && !target) {
                    if (dRow === direction) return true;
                    if (fromRow === startRow && dRow === 2 * direction && !this.board[fromRow + direction][fromCol]) return true;
                }
                if (absCol === 1 && dRow === direction && target) return true;
                return false;

            case 'r': // Rook
                if (dRow !== 0 && dCol !== 0) return false;
                return this.isPathClear(fromRow, fromCol, toRow, toCol);

            case 'n': // Knight
                return (absRow === 2 && absCol === 1) || (absRow === 1 && absCol === 2);

            case 'b': // Bishop
                if (absRow !== absCol) return false;
                return this.isPathClear(fromRow, fromCol, toRow, toCol);

            case 'q': // Queen
                if (dRow !== 0 && dCol !== 0 && absRow !== absCol) return false;
                return this.isPathClear(fromRow, fromCol, toRow, toCol);

            case 'k': // King
                return absRow <= 1 && absCol <= 1;
        }

        return false;
    }

    isPathClear(fromRow, fromCol, toRow, toCol) {
        const dRow = Math.sign(toRow - fromRow);
        const dCol = Math.sign(toCol - fromCol);

        let row = fromRow + dRow;
        let col = fromCol + dCol;

        while (row !== toRow || col !== toCol) {
            if (this.board[row][col]) return false;
            row += dRow;
            col += dCol;
        }

        return true;
    }

    updateStatus() {
        if (this.chessStatus) {
            this.chessStatus.textContent = this.isWhiteTurn ? 'White to move' : 'Black to move';
        }
        const statusEl = document.getElementById('chess-status');
        if (statusEl) {
            statusEl.textContent = 'in progress';
        }
    }

    newGame() {
        this.board = this.getStartingPosition();
        this.selectedSquare = null;
        this.isWhiteTurn = true;
        this.updateStatus();
        this.renderBoard();
    }

    async getHint() {
        // Simple hint: find a piece that can move
        if (this.chessStatus) {
            this.chessStatus.textContent = 'Thinking...';
        }

        // Find a random valid move
        const moves = [];
        for (let fromRow = 0; fromRow < 8; fromRow++) {
            for (let fromCol = 0; fromCol < 8; fromCol++) {
                const piece = this.board[fromRow][fromCol];
                if (!piece) continue;

                const isWhite = piece === piece.toUpperCase();
                if (isWhite !== this.isWhiteTurn) continue;

                for (let toRow = 0; toRow < 8; toRow++) {
                    for (let toCol = 0; toCol < 8; toCol++) {
                        if (this.isValidMove(fromRow, fromCol, toRow, toCol)) {
                            moves.push({ fromRow, fromCol, toRow, toCol });
                        }
                    }
                }
            }
        }

        if (moves.length > 0) {
            const hint = moves[Math.floor(Math.random() * moves.length)];
            const files = 'abcdefgh';
            const from = files[hint.fromCol] + (8 - hint.fromRow);
            const to = files[hint.toCol] + (8 - hint.toRow);
            this.chessStatus.textContent = `Try ${from} to ${to}`;
        } else {
            this.chessStatus.textContent = 'No moves available!';
        }
    }

    // ========== AMBIENT MOMENTS ==========
    initAmbientMoments() {
        // Ticker element for ambient moments
        this.createAmbientTicker();

        // Get an ambient moment now
        this.showAmbientMoment();

        // Show new ambient moments every 45-90 seconds
        this.scheduleNextAmbient();
    }

    createAmbientTicker() {
        // Check if ticker already exists
        if (document.getElementById('rec-ambient')) return;

        // Create the ambient ticker element
        const sidebar = document.querySelector('.sidebar-section[data-section="rec"]');
        if (!sidebar) return;

        const ticker = document.createElement('div');
        ticker.className = 'ambient-ticker';
        ticker.id = 'rec-ambient';
        ticker.innerHTML = '<span class="ambient-text"></span>';

        // Insert after the who's here panel
        const whosHere = sidebar.querySelector('.whos-here-panel');
        if (whosHere) {
            whosHere.after(ticker);
        } else {
            sidebar.appendChild(ticker);
        }

        this.ambientTicker = ticker;
    }

    async showAmbientMoment() {
        if (!this.ambientTicker) return;

        try {
            // Randomly pick bartender action or game table moment
            const endpoint = Math.random() < 0.6 ?
                `${this.baseUrl}/rec-room/bartender` :
                `${this.baseUrl}/games/moment`;

            const response = await fetch(endpoint);
            const data = await response.json();

            let momentText = '';
            if (data.action) {
                momentText = data.action;
            } else if (data.moment) {
                momentText = data.moment;
            } else if (data.happening) {
                momentText = data.happening;
            }

            if (momentText) {
                const textEl = this.ambientTicker.querySelector('.ambient-text');
                if (textEl) {
                    // Fade out
                    this.ambientTicker.classList.add('fading');
                    setTimeout(() => {
                        textEl.textContent = momentText;
                        this.ambientTicker.classList.remove('fading');
                    }, 300);
                }
            }
        } catch (error) {
            // Silent fail for ambient - not critical
        }
    }

    scheduleNextAmbient() {
        // Random interval between 45-90 seconds
        const delay = 45000 + Math.random() * 45000;
        setTimeout(() => {
            this.showAmbientMoment();
            this.scheduleNextAmbient();
        }, delay);
    }

    // ========== JUKEBOX / SPACE RADIO ==========
    initJukebox() {
        this.loadNowPlaying();
        this.loadCurrentDJ();

        // Poll for current track every 30 seconds
        setInterval(() => this.loadNowPlaying(), 30000);
        // Update DJ every 5 minutes
        setInterval(() => this.loadCurrentDJ(), 300000);

        // Request song button
        const requestBtn = document.getElementById('jukebox-request');
        if (requestBtn) {
            requestBtn.addEventListener('click', () => this.requestSong());
        }

        // Skip button
        const skipBtn = document.getElementById('jukebox-skip');
        if (skipBtn) {
            skipBtn.addEventListener('click', () => this.skipTrack());
        }
    }

    async loadCurrentDJ() {
        const djDisplay = document.getElementById('jukebox-dj');
        if (!djDisplay) return;

        try {
            const response = await fetch(`${this.baseUrl}/jukebox/dj`);
            const data = await response.json();

            if (data.current_dj) {
                djDisplay.textContent = `${data.current_dj} on air`;
                djDisplay.title = data.vibe;
            }
        } catch (error) {
            djDisplay.textContent = 'offline';
        }
    }

    async skipTrack() {
        try {
            await fetch(`${this.baseUrl}/jukebox/radio-skip`, { method: 'POST' });
            this.loadNowPlaying();
        } catch (error) {
            console.error('[Jukebox] Skip failed:', error);
        }
    }

    async loadNowPlaying() {
        if (!this.jukeboxDisplay) return;

        try {
            const response = await fetch(`${this.baseUrl}/jukebox/now-playing`);
            const data = await response.json();

            if (data.track) {
                const track = data.track;
                this.jukeboxDisplay.innerHTML = `
                    <span class="track-note">♫</span>
                    <span class="track-name">${track.name}</span>
                    ${track.artist ? `<span class="track-artist">— ${track.artist}</span>` : ''}
                    ${track.requested_by ? `<span class="track-dj">(${track.requested_by})</span>` : ''}
                `;
            } else if (data.queue && data.queue.length > 0) {
                // Show next in queue
                const next = data.queue[0];
                this.jukeboxDisplay.innerHTML = `
                    <span class="track-note">♫</span>
                    <span class="track-name">${next.name}</span>
                    <span class="track-status">up next</span>
                `;
            } else {
                this.jukeboxDisplay.innerHTML = '<span class="track-note">♫</span> silence';
            }
        } catch (error) {
            // Jukebox backend not available - show silence
            this.jukeboxDisplay.innerHTML = '<span class="track-note">♫</span> silence';
        }
    }

    async requestSong() {
        // Could open a modal or use the chat to request
        // For now, let a random crew member pick
        try {
            const response = await fetch(`${this.baseUrl}/jukebox/crew-pick`, { method: 'POST' });
            const data = await response.json();

            if (data.track) {
                this.loadNowPlaying();
            }
        } catch (error) {
            console.error('[Jukebox] Request failed:', error);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.recRoom = new RecRoom();
});
