const axios = require('axios');
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:5000';
const ITINERARY_BASE = process.env.ITINERARY_URL || 'http://localhost:5001'; // 5001 = BookSvc
const PROMO_BASE     = process.env.PROMO_URL     || 'http://localhost:5004';

exports.getItineraries = async (req, res) => {
  const resp = await axios.get(`${ITINERARY_BASE}/itineraries`, { params: req.query });
  res.json(resp.data);
};

exports.createReservation = async (req, res) => {
  try {
    const resp = await axios.post(`${BACKEND_URL}/api/reservations`, req.body);
    res.status(resp.status).json(resp.data);
  } catch (e) {
    res.status(e.response?.status || 500).json({ error: e.message });
  }
};

exports.cancelReservation = async (req, res) => {
  try {
    const { id } = req.params;
    const resp = await axios.delete(`${BACKEND_URL}/api/reservations/${id}`);
    res.status(resp.status).json(resp.data);
  } catch (e) {
    res.status(e.response?.status || 500).json({ error: e.message });
  }
};

exports.subscribePromotions = (req, res) => {
  const { clientId, destination } = req.params;
  axios.get(`${PROMO_BASE}/promotions/subscribe/${clientId}/${destination}`, { responseType:'stream' })
    .then(response => {
      res.set(response.headers);
      response.data.pipe(res);
    });
};

exports.unsubscribePromotions = async (req, res) => {
  await axios.post(`${PROMO_BASE}/promotions/unsubscribe`, { client_id: req.body.clientId });
  res.json({ status:'ok' });
};