function getToken() {
  return localStorage.getItem('access_token');
}

const isDemo = () => {
  const token = getToken();
  return !token || token.startsWith('demo_');
};

async function apiFetch(endpoint) {
  // Mode Démo / Hors-ligne / Isolée par entreprise
  if (isDemo()) {
    if (endpoint.startsWith('/products/')) {
      if (window.NexaTenant) {
        return window.NexaTenant.getData('products', []);
      }
      const stored = localStorage.getItem('demo_products');
      return stored ? JSON.parse(stored) : [];
    }
    if (endpoint.startsWith('/invoices/')) {
      if (window.NexaTenant) {
        return window.NexaTenant.getData('invoices', []);
      }
      const stored = localStorage.getItem('demo_invoices');
      return stored ? JSON.parse(stored) : [];
    }
    if (endpoint.startsWith('/warehouses/')) {
      return [
        { id: 1, name: "Entrepôt Principal", code: "WH-01" }
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

    if (!res.ok) throw new Error("API non disponible");
    return await res.json();
  } catch (err) {
    console.warn(`Erreur de connexion vers ${endpoint}, repli sur les données isolées de l'entreprise :`, err);
    if (endpoint.startsWith('/products/')) {
      return window.NexaTenant ? window.NexaTenant.getData('products', []) : [];
    }
    if (endpoint.startsWith('/invoices/')) {
      return window.NexaTenant ? window.NexaTenant.getData('invoices', []) : [];
    }
    return [];
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
  if (!data) {
    setKpi('kpi-produits', 0);
    setKpi('kpi-rupture', 0);
    return;
  }

  const total    = data.length;
  const rupture  = data.filter(p => (parseInt(p.stock ?? p.stock_quantity ?? 0, 10)) <= 0).length;
  setKpi('kpi-produits',  total);
  setKpi('kpi-rupture',   rupture);
}

async function chargerFactures() {
  const data = await apiFetch('/invoices/');
  if (!data || data.length === 0) {
    setKpi('kpi-ca', '0.00 €');
    setKpi('kpi-en-attente', 0);
    return;
  }

  const enAttente = data.filter(f => f.status === 'pending' || f.status === 'draft').length;
  const ca = data
    .filter(f => f.status === 'paid')
    .reduce((sum, f) => sum + (parseFloat(f.total_ttc) || 0), 0);

  setKpi('kpi-ca', ca.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €');
  setKpi('kpi-en-attente', enAttente);
}

function chargerClients() {
  let list = [];
  if (window.NexaTenant) {
    list = window.NexaTenant.getData('clients', []);
  } else {
    const stored = localStorage.getItem('demo_clients');
    if (stored) {
      try { list = JSON.parse(stored); } catch (_) { list = []; }
    }
  }
  setKpi('kpi-clients-total', list.length);
}

async function chargerCollaborateurs() {
  let count = 1;
  if (window.NexaTenant) {
    const users = window.NexaTenant.getData('users', []);
    count = users && users.length > 0 ? users.length : 1;
  }
  setKpi('kpi-entrepots', count);
}

function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (sidebar) sidebar.classList.toggle('collapsed');
}

let stockChartInstance = null;
async function dessinerchartStock() {
  const canvas = document.getElementById('chart-stock');
  if (!canvas) return;

  const data = await apiFetch('/products/');
  if (stockChartInstance) {
    stockChartInstance.destroy();
    stockChartInstance = null;
  }

  if (!data || data.length === 0) {
    stockChartInstance = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: ['Aucun produit'],
        datasets: [{
          label: 'Valeur stock (€)',
          data: [0],
          backgroundColor: '#e2e8f0',
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false }
        },
        scales: {
          y: { beginAtZero: true, max: 10 }
        }
      }
    });
    return;
  }

  const noms = data.map(p => {
    const name = p.name || p.designation || 'Article';
    return name.length > 15 ? name.substring(0, 15) + '...' : name;
  });
  const valeurs = data.map(p => {
    const price = parseFloat(p.price ?? p.price_ht ?? 0) || 0;
    const stock = parseInt(p.stock ?? p.stock_quantity ?? 0, 10) || 0;
    return price * stock;
  });

  stockChartInstance = new Chart(canvas, {   
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

let facturesChartInstance = null;
async function dessinerchartFactures() {
  const canvas = document.getElementById('chart-factures');
  if (!canvas) return;

  const data = (await apiFetch('/invoices/')) || [];
  if (facturesChartInstance) {
    facturesChartInstance.destroy();
    facturesChartInstance = null;
  }

  const payees    = data.filter(f => f.status === 'paid').length;
  const enAttente = data.filter(f => f.status === 'pending' || f.status === 'draft').length;
  const annulees  = data.filter(f => f.status === 'cancelled').length;
  const total = payees + enAttente + annulees;

  if (total === 0) {
    facturesChartInstance = new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels: ['Aucune facture'],
        datasets: [{
          data: [1],
          backgroundColor: ['#e2e8f0'],
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
          },
          tooltip: { enabled: false }
        }
      }
    });
    return;
  }

  facturesChartInstance = new Chart(canvas, { 
    type: 'doughnut',
    data: {
      labels: ['Payées', 'En attente', 'Annulées'],
      datasets: [{
        data: [payees, enAttente, annulees],
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
  await chargerCollaborateurs();
  await dessinerchartStock();
  await dessinerchartFactures();
}

document.getElementById('toggle-sidebar')?.addEventListener('click', toggleSidebar);

init();
