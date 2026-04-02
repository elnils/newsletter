document.getElementById('action-btn').addEventListener('click', () => {
    const messageElement = document.getElementById('message');
    messageElement.textContent = "Hallo! Es funktioniert!";
    console.log("Button wurde gedrückt.");
});
