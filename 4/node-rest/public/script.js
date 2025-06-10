const form = document.getElementById('searchForm');
const tripsBody = document.getElementById('tripsBody');
const promosContainer = document.getElementById('promosContainer');
let es;

form.addEventListener('submit', async e => {
  e.preventDefault();
  const q = new URLSearchParams(new FormData(form));
  const res = await fetch(`/api/itineraries?${q}`);
  const trips = await res.json();
  tripsBody.innerHTML = trips.map(t => `
    <tr>
      <td>${t.departure_date}</td>
      <td>${t.ship}</td>
      <td>${t.departure_harbor}</td>
      <td>${t.arrival_harbor}</td>
      <td>${t.number_of_days}</td>
      <td>$${t.price}</td>
      <td>
        <button onclick="book('${t.id}',${t.price})">Reservar</button>
        <button onclick="subscribeToDestination('${t.arrival_harbor}')">Inscrever</button>
      </td>
    </tr>
  `).join('');
});

async function book(trip_id, price) {
  const res = await fetch('/api/reservations', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({trip_id, price, passengers:1})
  });
  const { reservation_id } = await res.json();
  alert(`Reserva criada: ${reservation_id}`);
}

function subscribeToDestination(dest) {
  if (es) es.close();
  promosContainer.innerHTML = '';
  es = new EventSource(`/api/promotions/subscribe/${dest.toLowerCase()||''}`);
  es.onmessage = e => {
    const p = JSON.parse(e.data);
    const card = document.createElement('div');
    card.innerHTML = `
      <div class="promotion-card">
        <span class="discount">${p.discount}% OFF</span>
        <h3>${p.destination}</h3>
        <p>${p.description}</p>
        <p class="expiry">Expira em ${p.expires_in}</p>
      </div>`;
    promosContainer.prepend(card);
  };
}

document.getElementById('btnUnsub').onclick = () => {
  if (es) es.close();
};