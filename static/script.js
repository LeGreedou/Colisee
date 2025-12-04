async function refreshData() {
    try {
        // Le paramètre ?t= empêche le navigateur de garder le JSON en cache
        const response = await fetch('/static/data.json?t=' + Date.now());
        const data = await response.json();
        const container = document.getElementById('dashboard');
        
        container.innerHTML = ''; // On nettoie l'écran avant de reconstruire

        data.accounts.forEach(acc => {
            const card = document.createElement('div');
            card.className = 'player-card';

            // --- 1. CALCUL DES STATS GLOBALES (SESSION) ---
            let totalGames = 0;
            let totalLPGain = 0;

            if (acc.matches) {
                totalGames = acc.matches.length;
                acc.matches.forEach(m => {
                    // On additionne seulement si c'est un vrai nombre (pas "?")
                    if (m.lp_change !== "?" && m.lp_change !== null) {
                        totalLPGain += parseInt(m.lp_change);
                    }
                });
            }

            // Gestion du signe + et de la couleur pour le total affiché en haut
            const signTotal = totalLPGain > 0 ? '+' : '';
            const colorTotal = totalLPGain >= 0 ? 'var(--win-color)' : 'var(--loss-color)';

            // --- NOUVEAU : GESTION DU WINRATE ---
            // On récupère le winrate calculé par Python, ou 0 par défaut
            const winrate = acc.winrate !== undefined ? acc.winrate : 0;
            // Couleur : Vert (#4ade80) si >= 50%, Rouge (#f87171) sinon
            const wrColor = winrate >= 50 ? '#4ade80' : '#f87171';

            // --- 2. LOGIQUE D'AFFICHAGE DU RANG ---
            const apexTiers = ['MASTER', 'GRANDMASTER', 'CHALLENGER'];
            let rankText = '';
            
            if (acc.rank_info.tier === 'UNRANKED') {
                rankText = 'Unranked';
            } else if (apexTiers.includes(acc.rank_info.tier)) {
                // Master+ : Pas de division (I, II...)
                rankText = `${acc.rank_info.tier} • ${acc.rank_info.lp} LP`;
            } else {
                // Classique : GOLD II
                rankText = `${acc.rank_info.tier} ${acc.rank_info.rank} • ${acc.rank_info.lp} LP`;
            }

            // --- 3. CONSTRUCTION DE LA LISTE DES MATCHS ---
            let matchesHtml = '';
            
            if (acc.matches && acc.matches.length > 0) {
                acc.matches.forEach(match => {
                    const isWin = match.resultat === "Victoire";
                    const cssClass = isWin ? 'win' : 'loss';
                    
                    // Gestion de l'affichage du LP (+15, -12, ou ?)
                    let lpDisplay = match.lp_change;
                    if (match.lp_change !== "?" && match.lp_change > 0) {
                        lpDisplay = "+" + match.lp_change;
                    }

                    // Construction de la ligne
                    matchesHtml += `
                        <div class="match-row ${cssClass}">
                            
                            <div class="champ-info">
                                <div class="champ-icon-wrapper">
                                    <img src="${match.icon}" class="champ-icon zoom-effect" alt="${match.champion}">
                                </div>
                                <span>${match.champion}</span>
                            </div>

                            <div class="match-center">
                                <div class="match-result">${match.resultat}</div>
                                <div class="match-kda">${match.kda ? match.kda : ''}</div>
                            </div>

                            <div class="lp-change">
                                ${lpDisplay} LP
                            </div>

                        </div>
                    `;
                });
            } else {
                matchesHtml = '<div style="padding:20px; text-align:center; color:#555;">Aucun match sur la période</div>';
            }

            // --- 4. ASSEMBLAGE FINAL DE LA CARTE ---
            card.innerHTML = `
                <div class="card-header">
                    <a href="${acc.dpm}" target="_blank" class="player-name-link">
                        ${acc.gameName} <span class="player-tag">#${acc.tagLine}</span>
                    </a>                    
                    <div class="header-infos-row">
                        <div class="rank-display">${rankText}</div>
                        
                        <div class="session-stats">
                            <div class="stat-games">${totalGames} Game${totalGames > 1 ? 's' : ''}</div>
                            
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <div class="stat-lp" style="color: ${colorTotal}">
                                    ${signTotal}${totalLPGain} LP
                                </div>
                                <div class="stat-winrate" style="color: ${wrColor}; font-weight: bold; font-size: 0.9em;">
                                    ${winrate}% WR
                                </div>
                            </div>

                        </div>
                    </div>
                </div>

                <div class="match-history">
                    ${matchesHtml}
                </div>
            `;
            
            container.appendChild(card);
        });

    } catch (e) {
        console.error("Erreur chargement JSON:", e);
    }
}

// Lancer au démarrage
refreshData();

// Rafraîchir toutes les 60 secondes
setInterval(refreshData, 60000);