// auth-guard.js : Vérifie si l'utilisateur est authentifié avant d'afficher la page
(function () {
    const token = localStorage.getItem("access_token");

    // Si aucun token n'est trouvé, l'utilisateur n'est pas connecté
    if (!token) {
        window.location.href = "index.html";
        return;
    }

    // Vérification optionnelle de la validité du token auprès de l'API FastAPI
    fetch("http://localhost:8000/api/v1/auth/me", {
        method: "GET",
        headers: {
            "Authorization": `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) {
            // Token expiré ou invalide -> suppression et redirection vers la connexion
            localStorage.removeItem("access_token");
            window.location.href = "index.html";
        }
    })
    .catch(error => {
        console.error("Erreur de connexion avec le serveur d'authentification :", error);
    });
})();