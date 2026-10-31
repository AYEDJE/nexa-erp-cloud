function getToken() {
  return localStorage.getItem('access_token');
}

const isDemo = () => {
  const token = getToken();
  return !token || token.startsWith('demo_');
};

async function apiFetch(endpoint) {
  // Mode Démo / Hors-ligne
  if (isDemo()) {
    if (endpoint.startsWith('/products/')) {
      const stored = localStorage.getItem('demo_products');
      if (stored) return JSON.parse(stored);
      return [
        { id: 1, name: "Ordinateur Portable Pro 15\"", price: 850.0, stock: 12 },
        { id: 2, name: "Écran 27\" 4K UHD", price: 320.0, stock: 8 },
        { id: 3, name: "Clavier Mécanique Sans Fil", price: 89.90, stock: 25 },
        { id: 4, name: "Souris Ergonomique", price: 45.0, stock: 3 },
        { id: 5, name: "Imprimante Laser Multifonction", price: 290.0, stock: 0 }
      ];
    }
    if (endpoint.startsWith('/invoices/')) {
      const stored = localStorage.getItem('demo_invoices');
      if (stored) return JSON.parse(stored);
      return [
        { id: 1, number: "FAC-202610-001", total_ttc: 1785.0, status: "paid" },
        { id: 2, number: "FAC-202610-002", total_ttc: 1011.5, status: "pending" },
        { id: 3, number: "DEV-202610-003", total_ttc: 3808.0, status: "pending" }
      ];
    }
    if (endpoint.startsWith('/warehouses/')) {
      return [
        { id: 1, name: "Entrepôt Principal - Tunis", code: "WH-TUNIS" },
        { id: 2, name: "Dépôt Logistique - Sfax", code: "WH-SFAX" }
      ];
    }
    return [];
  }

  // Mode API Réel
  try {
    const res = await fetch(`${API}${endpoint}`, {
      headers: {
        'Authorization': 'Bearer ' + getToken()
      }
    });

    if (res.status === 401) {
      console.warn("Session expirée ou non autorisée");
      return null;
    }

    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.warn(`Erreur de connexion vers ${endpoint}, repli local :`, err);
    return null;
  }
}

function afficherDate() {
  const el = document.getElementById('current-date');
  if (!el) return;
  const now = new Date();
  el.textContent = '📅 ' + now.toLocaleDateString('fr-FR', {
    day: '2-digit', month: 'long', year: 'numeric'
  });
}

function setKpi(id, valeur) {
  const el = document.getElementById(id);
  if (el) el.textContent = valeur;
}

async function chargerProduits() {
  const data = await apiFetch('/products/');
  if (!data) return;

  const total    = data.length;
  const rupture  = data.filter(p => (p.stock || p.stock_quantity || 0) === 0).length;
  setKpi('kpi-produits',  total);
  setKpi('kpi-rupture',   rupture);
}

async function chargerFactures() {
  const data = await apiFetch('/invoices/');
  if (!data) return;

  const enAttente = data.filter(f => f.status === 'pending' || f.status === 'draft').length;
  const ca = data
    .filter(f => f.status === 'paid')
    .reduce((sum, f) => sum + (parseFloat(f.total_ttc) || 0), 0);

  setKpi('kpi-ca',         ca.toLocaleString('fr-FR', { minimumFractionDigits: 2 }) + ' €');
  setKpi('kpi-en-attente', enAttente);
}

function chargerClients() {
  const stored = localStorage.getItem('demo_clients');
  if (stored) {
    const list = JSON.parse(stored);
    setKpi('kpi-clients-total', list.length);
  } else {
    setKpi('kpi-clients-total', '4');
  }
}

async function chargerEntrepots() {
  const data = await apiFetch('/warehouses/');
  if (!data) {
    setKpi('kpi-entrepots', '5');
    return;
  }
  setKpi('kpi-entrepots', data.length);
}

function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (sidebar) sidebar.classList.toggle('collapsed');
}

async function dessinerchartStock() {
  const canvas = document.getElementById('chart-stock');
  if (!canvas) return;

  const data = await apiFetch('/products/');
  if (!data || data.length === 0) return;

  const noms    = data.map(p => p.name.length > 15 ? p.name.substring(0, 15) + '...' : p.name);
  const valeurs = data.map(p => (p.price || 0) * (p.stock || p.stock_quantity || 0));

  new Chart(canvas, {   
    type: 'bar',
    data: {
      labels: noms,
      datasets: [{
        label: 'Valeur stock (€)',
        data: valeurs,
        backgroundColor: '#1a73e8',
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {                                       
            callback: val => val.toLocaleString('fr-FR') + ' €'
          }
        }
      }
    }
  });                                                     
}

async function dessinerchartFactures() {
  const canvas = document.getElementById('chart-factures');
  if (!canvas) return;

  const data = await apiFetch('/invoices/');
  if (!data || data.length === 0) return;

  const payees    = data.filter(f => f.status === 'paid').length;
  const enAttente = data.filter(f => f.status === 'pending' || f.status === 'draft').length;
  const annulees  = data.filter(f => f.status === 'cancelled').length;

  new Chart(canvas, { 
    type: 'doughnut',
    data: {
      labels: ['Payées', 'En attente', 'Annulées'],
      datasets: [{
        data: [payees || 1, enAttente || 2, annulees || 0],
        backgroundColor: ['#16a34a', '#d97706', '#dc2626'],
        borderWidth: 0                                    
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '70%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { padding: 14, font: { size: 12 } }
        }
      }
    }
  });                                                     
}

async function init() {
  afficherDate();
  await chargerProduits();
  await chargerFactures();
  chargerClients();
  await chargerEntrepots();
  await dessinerchartStock();
  await dessinerchartFactures();
}

document.getElementById('toggle-sidebar')?.addEventListener('click', toggleSidebar);

init();
