let ws;
const auctionId = 1; // Default for demo

function connectWebSocket() {
    ws = new WebSocket(`ws://${window.location.host}/ws/bid/${auctionId}`);
    
    ws.onopen = () => {
        document.getElementById('conn-status').innerText = "Connected";
        document.getElementById('conn-status').style.color = "green";
        addLog("System", "Connected to BidMind Engine");
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'new_bid') {
            document.getElementById('pred-price').innerText = `$${data.ai_prediction}`;
            addLog(`User ${data.user_id}`, `$${data.amount} (AI Forecast: $${data.ai_prediction})`);
        } else if (data.status === 'rejected') {
            alert("⚠️ " + data.reason);
        }
    };

    ws.onclose = () => {
        document.getElementById('conn-status').innerText = "Disconnected";
        document.getElementById('conn-status').style.color = "red";
        setTimeout(connectWebSocket, 3000); // Auto-reconnect
    };
}

function placeBid() {
    const amount = document.getElementById('bidAmount').value;
    const userId = document.getElementById('userId').value;
    if(ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            auction_id: auctionId,
            amount: parseFloat(amount),
            user_id: userId,
            starting_price: 100,
            duration: 24,
            time_left: 30
        }));
    } else {
        alert("Not connected to server");
    }
}

async function createAuction() {
    const title = document.getElementById('title').value;
    const desc = document.getElementById('desc').value;
    const price = document.getElementById('startPrice').value;

    const res = await fetch('/api/auctions', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({title, description: desc, starting_price: price})
    });
    const data = await res.json();
    document.getElementById('ai-analysis-result').innerText = 
        "AI Analysis: " + JSON.stringify(data.ai_analysis);
}

function addLog(user, msg) {
    const log = document.getElementById('bidLog');
    const div = document.createElement('div');
    div.className = 'log-entry';
    div.innerHTML = `<span><strong>${user}</strong></span> <span>${msg}</span>`;
    log.prepend(div);
}

connectWebSocket();