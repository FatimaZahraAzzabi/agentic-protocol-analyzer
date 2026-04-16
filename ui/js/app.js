// Configuration API
const API_BASE = 'http://localhost:5000/api';

// Éléments DOM
const form = document.getElementById('protocolForm');
const protocolInput = document.getElementById('protocol');
const btnAnalyze = document.getElementById('btnAnalyze');
const workflowCard = document.getElementById('workflowCard');
const resultCard = document.getElementById('resultCard');
const placeholderCard = document.getElementById('placeholderCard');

// Gestion du formulaire
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const protocol = protocolInput.value.trim();
    
    if (!protocol) {
        alert('Veuillez entrer un protocole');
        return;
    }
    
    await analyzeProtocol(protocol);
});

// Boutons d'exemples
document.querySelectorAll('.example-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const example = btn.getAttribute('data-protocol');
        protocolInput.value = example;
    });
});

// Fonction principale d'analyse
async function analyzeProtocol(protocol) {
    // UI: Afficher workflow, masquer placeholder
    workflowCard.style.display = 'block';
    placeholderCard.style.display = 'none';
    resultCard.style.display = 'none';
    btnAnalyze.disabled = true;
    btnAnalyze.innerHTML = '<i class="bi bi-hourglass-split"></i> Analyse en cours...';
    
    try {
        // Étape 1: Récupération normes
        updateStep('step-retrieve', 'active');
        
        // Appel API
        const response = await fetch(`${API_BASE}/audit-fabrication`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ protocol: protocol })
        });
        
        if (!response.ok) throw new Error('Erreur serveur');
        
        const data = await response.json();
        
        // Étape 2: Analyse terminée
        updateStep('step-retrieve', 'completed');
        updateStep('step-analyze', 'completed');
        
        // Vérifier si validation humaine requise
        if (data.compliance_result.score_risque >= 6) {
            updateStep('step-validate', 'active');
            document.getElementById('humanValidationSection').style.display = 'block';
        } else {
            updateStep('step-validate', 'completed');
            document.getElementById('humanValidationSection').style.display = 'none';
        }
        
        // Étape 3: Rapport généré
        updateStep('step-report', 'completed');
        
        // Afficher résultats
        displayResults(data.compliance_result);
        resultCard.style.display = 'block';
        
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors de l\'analyse: ' + error.message);
    } finally {
        btnAnalyze.disabled = false;
        btnAnalyze.innerHTML = '<i class="bi bi-play-fill"></i> Lancer l\'Audit ISO 22716';
    }
}

// Mise à jour visuelle des étapes
function updateStep(stepId, status) {
    const step = document.getElementById(stepId);
    step.className = `step ${status}`;
}

// Affichage des résultats
function displayResults(result) {
    const score = result.score_risque || 0;
    const conformite = result.conformite_globale || 'ERREUR';
    
    // Score circulaire
    const scoreCircle = document.getElementById('riskScore');
    document.getElementById('scoreValue').textContent = score;
    scoreCircle.className = 'risk-score-circle ' + 
        (score < 3 ? 'low' : score < 7 ? 'medium' : 'high');
    
    // Label conformité
    const label = document.getElementById('conformiteLabel');
    const header = document.getElementById('resultHeader');
    const title = document.getElementById('resultTitle');
    
    if (conformite === 'CONFORME') {
        label.textContent = '✅ Protocole Conforme';
        label.className = 'mt-2 fw-bold text-success';
        header.className = 'card-header conforme';
        title.innerHTML = '<i class="bi bi-check-circle"></i> Audit Réussi';
    } else {
        label.textContent = '❌ Non Conforme';
        label.className = 'mt-2 fw-bold text-danger';
        header.className = 'card-header non-conforme';
        title.innerHTML = '<i class="bi bi-x-circle"></i> Violations Détectées';
    }
    
    // Violations
    const violationsList = document.getElementById('violationsList');
    violationsList.innerHTML = '';
    if (result.violations && result.violations.length > 0) {
        result.violations.forEach(v => {
            const li = document.createElement('li');
            li.className = 'list-group-item violation-item';
            li.innerHTML = `
                <strong>${v.etape || 'Général'}</strong>: ${v.ecart}
                <br><small class="text-muted"><i class="bi bi-book"></i> ${v.reference_iso || 'ISO 22716'}</small>
            `;
            violationsList.appendChild(li);
        });
    } else {
        violationsList.innerHTML = '<li class="list-group-item">Aucune violation détectée</li>';
    }
    
    // Actions correctives
    const actionsList = document.getElementById('actionsList');
    actionsList.innerHTML = '';
    if (result.actions_correctives && result.actions_correctives.length > 0) {
        result.actions_correctives.forEach(action => {
            const li = document.createElement('li');
            li.className = 'list-group-item action-item';
            li.textContent = action;
            actionsList.appendChild(li);
        });
    }
}

// Validation humaine (simulation)
function validateHuman(approved) {
    const section = document.getElementById('humanValidationSection');
    if (approved) {
        section.innerHTML = '<div class="alert alert-success"><i class="bi bi-check-circle"></i> Protocole validé par le responsable qualité</div>';
        updateStep('step-validate', 'completed');
    } else {
        section.innerHTML = '<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Protocole rejeté - Modifications requises</div>';
    }
}

// Télécharger rapport (simulation)
function downloadReport() {
    alert('Fonctionnalité PDF en cours de développement...\n(Utilisez l\'endpoint /api/download-pdf)');
}

// Animation au chargement
window.addEventListener('load', () => {
    document.body.style.opacity = '0';
    setTimeout(() => {
        document.body.style.transition = 'opacity 0.5s';
        document.body.style.opacity = '1';
    }, 100);
});