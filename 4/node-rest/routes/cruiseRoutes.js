const express = require('express');
const router = express.Router();
const ctrl = require('../controllers/cruiseController');

router.post('/reservations',      ctrl.createReservation);
router.delete('/reservations/:id',ctrl.cancelReservation);
router.get('/promotions/subscribe/:destination', ctrl.subscribePromotions);
router.post('/promotions/unsubscribe',           ctrl.unsubscribePromotions);
router.get('/itineraries', ctrl.getItineraries);

module.exports = router;