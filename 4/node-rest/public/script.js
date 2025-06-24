// --- Elements for Cruise Search ---
const departureHarborSelect = document.getElementById('departure_harbor');
const arrivalHarborSelect = document.getElementById('arrival_harbor');
const departureDateInput = document.getElementById('departure_date');
const searchButton = document.getElementById('searchButton');
const resultsArea = document.getElementById('resultsArea'); // Area for cruise search results

// --- Elements for Promotion Subscription ---
const promotionEmailInput = document.getElementById('promotion_email');
const subscribeCheckbox = document.getElementById('subscribe_checkbox');
const updateSubscriptionButton = document.getElementById('updateSubscriptionButton');
const promotionsContainer = document.getElementById('promotions-container'); // Area for promotion cards

// --- Elements for Booking Modal ---
const bookingModal = document.getElementById('bookingModal');
const closeButton = document.querySelector('.close-button');
const modalItineraryId = document.getElementById('modal_itinerary_id');
const modalMaxPassengers = document.getElementById('modal_max_passengers'); // New element for max passengers
const modalMaxCabins = document.getElementById('modal_max_cabins');     // New element for max cabins
const numPassengersInput = document.getElementById('num_passengers');
const numCabinsInput = document.getElementById('num_cabins');
const confirmBookingButton = document.getElementById('confirmBookingButton');
const bookingResultArea = document.getElementById('bookingResultArea');

// --- Elements for Cancel Reservation ---
const cancelReservationCodeInput = document.getElementById('cancel_reservation_code');
const cancelReservationButton = document.getElementById('cancelReservationButton');

// --- General Message Area ---
const messageArea = document.getElementById('messageArea');

// Variable to hold the EventSource instance for SSE
let eventSource = null;

// Stores the currently selected itinerary ID for booking
let currentBookingItineraryId = null;

// Stores the fetched cruise data for quick lookup by itinerary ID
let fetchedCruisesMap = new Map();

// Map to store active polling intervals for reservations (kept for potential future use, but not called)
const activeReservationPolling = new Map();

// --- Helper Functions ---

/**
 * Displays a message in the designated message area.
 * @param {string} message - The message text to display.
 * @param {string} type - 'error' (red) or 'success' (green) or 'info' (blue) or 'neutral' (gray) for styling.
 * @param {HTMLElement} [targetArea=messageArea] - The HTML element where the message should be displayed. Defaults to messageArea.
 */
function showMessage(message, type = 'error', targetArea = messageArea) {
    targetArea.innerHTML = message; // Use innerHTML to allow for <a> tags in success messages
    targetArea.classList.remove('hidden', 'bg-red-100', 'text-red-700', 'bg-green-100', 'text-green-700', 'bg-blue-100', 'text-blue-700', 'bg-gray-100', 'text-gray-700');
    if (type === 'error') {
        targetArea.classList.add('bg-red-100', 'text-red-700');
    } else if (type === 'success') {
        targetArea.classList.add('bg-green-100', 'text-green-700');
    } else if (type === 'info') {
        targetArea.classList.add('bg-blue-100', 'text-blue-700');
    } else if (type === 'neutral') { // For general booking messages
        targetArea.classList.add('bg-gray-100', 'text-gray-700');
    }
    targetArea.classList.remove('hidden');
}

/**
 * Clears any message displayed in a target area.
 * @param {HTMLElement} [targetArea=messageArea] - The HTML element whose messages should be cleared. Defaults to messageArea.
 */
function clearMessage(targetArea = messageArea) {
    targetArea.classList.add('hidden');
    targetArea.textContent = '';
}

/**
 * Displays the cruise search results.
 * @param {Array<Object>} cruises - An array of cruise objects to display.
 */
function displayCruises(cruises) {
    resultsArea.innerHTML = ''; // Clear previous results
    clearMessage(); // Clear any error messages from general message area

    // Clear and populate the map with new cruise data
    fetchedCruisesMap.clear();
    cruises.forEach(cruise => {
        // Ensure the ID is stored as a number in the map, matching its type from backend
        fetchedCruisesMap.set(parseInt(cruise.id, 10), cruise);
    });

    if (cruises && cruises.length > 0) {
        cruises.forEach(cruise => {
            const cruiseCard = document.createElement('div');
            cruiseCard.className = 'bg-white p-6 rounded-lg shadow-md border border-gray-200 transition-transform duration-200 hover:scale-[1.02]';
            cruiseCard.innerHTML = `
                <h3 class="text-xl font-bold text-gray-800 mb-2">${cruise.ship}</h3>
                <p class="text-gray-600 mb-1">Itinerary ID: <span class="font-semibold">${cruise.id}</span></p>
                <p class="text-gray-600 mb-1">Departure: <span class="font-semibold">${cruise.departure_harbor} at ${cruise.departure_time || 'N/A'}</span></p>
                <p class="text-gray-600 mb-1">Arrival: <span class="font-semibold">${cruise.arrival_harbor} on ${cruise.arrival_date || 'N/A'}</span></p>
                <p class="text-gray-600 mb-1">Visits: <span class="font-semibold">${cruise.visiting_harbors.join(', ')}</span></p>
                <p class="text-gray-600 mb-1">Duration: <span class="font-semibold">${cruise.number_of_days} days</span></p>
                <p class="text-lg font-bold text-indigo-600 mt-3">Price: R$ ${cruise.price.toFixed(2)}</p>
                <p class="text-sm text-gray-500 mt-2">Available Cabins: ${cruise.remaining_cabinets} | Available Passengers: ${cruise.remaining_passengers}</p>
                <button class="mt-4 w-full bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded-md transition-colors duration-200 book-now-btn" data-itinerary-id="${cruise.id}">
                    Book Now
                </button>
            `;
            resultsArea.appendChild(cruiseCard);
        });

        // Attach event listeners to the "Book Now" buttons
        document.querySelectorAll('.book-now-btn').forEach(button => {
            button.addEventListener('click', (event) => {
                const itineraryId = event.target.dataset.itineraryId;
                openBookingModal(itineraryId);
            });
        });

    } else {
        showMessage('No itineraries found for the selected search criteria.', 'info');
    }
}

/**
 * Adds a new promotion card to the promotions container.
 * @param {Object} promotion - The promotion object received via SSE.
 */
function addPromotionCard(promotion) {
    // Clear initial SSE connection message if present
    if (promotionsContainer.querySelector('#initial-sse-message')) {
        promotionsContainer.querySelector('#initial-sse-message').remove();
    }

    const card = document.createElement('div');
    card.className = 'promotion-card bg-white p-6 rounded-lg shadow-lg border border-red-200 mb-4 transform transition-transform duration-300 hover:scale-[1.01]';

    card.innerHTML = `
        <div class="discount text-white bg-red-500 py-1 px-3 rounded-br-lg font-bold absolute top-0 right-0 transform rotate-3 translate-x-4 -translate-y-2 shadow-md">
            -${promotion.discount}%
        </div>
        <h3 class="text-xl font-bold text-gray-900 mb-2">${promotion.title}</h3>
        <p class="text-gray-700 mb-3">${promotion.description}</p>
        <div class="flex items-baseline mb-2">
            <span class="original-price text-gray-500 line-through mr-2 text-sm">R$ ${promotion.original_price.toFixed(2)}</span>
            <span class="discounted-price text-red-600 font-extrabold text-2xl">R$ ${promotion.discounted_price.toFixed(2)}</span>
        </div>
        <p class="text-gray-600 text-sm mb-1">Departure Date: <span class="font-semibold">${promotion.departure_date}</span></p>
        <p class="text-gray-600 text-xs mt-2">Offer expires in <span class="font-semibold">${promotion.expires_in} hours</span></p>
        <button class="mt-4 w-full bg-indigo-500 hover:bg-indigo-600 text-white font-bold py-2 px-4 rounded-md transition-colors duration-200">
            View Deal
        </button>
    `;

    // Add to container, newest on top
    promotionsContainer.prepend(card);

    // Limit the number of promotion cards to prevent infinite growth
    while (promotionsContainer.children.length > 5) { // Keep max 5 promotions
        promotionsContainer.removeChild(promotionsContainer.lastChild);
    }
}


/**
 * Establishes an SSE connection for a given email.
 * @param {string} email - The email to use for the SSE connection.
 */
function connectSSE(email) {
    if (eventSource) {
        eventSource.close(); // Close existing connection before opening a new one
        console.log('Existing SSE connection closed.');
    }

    // Pass email as a query parameter for the SSE endpoint
    eventSource = new EventSource(`/api/promotions/sse?email=${encodeURIComponent(email)}`);

    eventSource.onopen = () => {
        console.log('SSE connection opened.');
        showMessage('Connected to promotion stream. Waiting for promotions...', 'info');
        // Initial message for promotions container
        promotionsContainer.innerHTML = `<p id="initial-sse-message" class="text-gray-600 text-center">Connecting to promotions stream...</p>`;
    };

    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.message === "SSE connection established.") {
                console.log(data.message); // Log initial connection message
            } else {
                addPromotionCard(data); // Add promotion card to UI
            }
        } catch (e) {
            console.error('Error parsing SSE message:', e, event.data);
        }
    };

    eventSource.onerror = (error) => {
        console.error('SSE Error:', error);
        // Do not display an error message if the stream closes due to a deliberate disconnect
        // This check is a simple heuristic; a more robust solution might track the intent of disconnection.
        if (eventSource && eventSource.readyState === EventSource.CLOSED) {
             console.log('SSE connection closed intentionally or by server.');
             showMessage('Disconnected from promotion stream.', 'info');
             promotionsContainer.innerHTML = `<p class="text-gray-600 text-center">Disconnected from promotions.</p>`;
        } else {
            showMessage('Error receiving promotions. Please check your subscription status or try again later.', 'error');
            promotionsContainer.innerHTML = `<p class="text-gray-600 text-center">Error: Could not connect to promotions stream.</p>`;
        }
        eventSource.close(); // Ensure connection is closed on error
        eventSource = null;
        subscribeCheckbox.checked = false; // Uncheck checkbox to reflect disconnected state
    };
}

/**
 * Closes the existing SSE connection.
 */
function disconnectSSE() {
    if (eventSource) {
        eventSource.close();
        eventSource = null;
        console.log('SSE connection closed manually.');
        showMessage('Disconnected from promotion stream.', 'info');
        promotionsContainer.innerHTML = `<p class="text-gray-600 text-center">Disconnected from promotions.</p>`;
    }
}

/**
 * Opens the booking modal for a specific itinerary.
 * @param {string} itineraryId - The ID of the itinerary to book.
 */
function openBookingModal(itineraryId) {
    // Convert itineraryId to number, as it's passed as a string from dataset
    currentBookingItineraryId = parseInt(itineraryId, 10);
    modalItineraryId.textContent = itineraryId; // Display the original string ID in modal for user

    // Get the cruise data using the numeric ID
    const cruise = fetchedCruisesMap.get(currentBookingItineraryId);
    if (cruise) {
        // Use remaining_passengers and remaining_cabinets received from the backend
        modalMaxPassengers.textContent = cruise.remaining_passengers;
        modalMaxCabins.textContent = cruise.remaining_cabinets;

        // Set max attribute for input fields to prevent exceeding available
        numPassengersInput.max = cruise.remaining_passengers;
        numCabinsInput.max = cruise.remaining_cabinets;
        numPassengersInput.value = 1; // Reset to default
        numCabinsInput.value = 1;     // Reset to default

        // Add client-side visual validation (e.g., if value > max)
        // Ensure input values don't exceed max or go below 1
        numPassengersInput.addEventListener('input', () => {
            const val = parseInt(numPassengersInput.value);
            if (isNaN(val) || val < 1) {
                numPassengersInput.value = 1;
            } else if (val > cruise.remaining_passengers) {
                numPassengersInput.value = cruise.remaining_passengers;
            }
        });
        numCabinsInput.addEventListener('input', () => {
            const val = parseInt(numCabinsInput.value);
            if (isNaN(val) || val < 1) {
                numCabinsInput.value = 1;
            } else if (val > cruise.remaining_cabinets) {
                numCabinsInput.value = cruise.remaining_cabinets;
            }
        });

    } else {
        console.error(`Cruise data not found in map for itinerary ID: ${itineraryId} (type: ${typeof itineraryId}, parsed: ${currentBookingItineraryId})`);
        showMessage(`Error: Cruise details not found for ID: ${itineraryId}. Please try searching again.`, 'error');
        closeBookingModal();
        return;
    }

    clearMessage(bookingResultArea); // Clear previous booking messages
    bookingModal.style.display = 'flex'; // Use flex to center
}

/**
 * Closes the booking modal.
 */
function closeBookingModal() {
    bookingModal.style.display = 'none';
    currentBookingItineraryId = null;
    
    // Close any active SSE connections when modal closes
    if (window.activeSSEConnections) {
        window.activeSSEConnections.forEach(eventSource => {
            if (eventSource.readyState !== EventSource.CLOSED) {
                eventSource.close();
                console.log('Closed SSE connection due to modal close');
            }
        });
        window.activeSSEConnections = [];
    }
}

/**
 * Starts SSE monitoring for reservation status updates
 * @param {string} reservation_id - The reservation ID to monitor
 * @param {HTMLElement} targetArea - The area to display status updates
 */
function startReservationStatusMonitoring(reservation_id, targetArea) {
    // Initialize global SSE connections array if not exists
    if (!window.activeSSEConnections) {
        window.activeSSEConnections = [];
    }
    
    // Create initial status message
    let statusMessageDiv = document.createElement('div');
    statusMessageDiv.id = `status-${reservation_id}`;
    statusMessageDiv.classList.add('mt-4', 'p-3', 'rounded-lg');
    
    // Set initial processing state
    updateStatusMessage(statusMessageDiv, 'processing', 'Processing payment...', reservation_id);
    targetArea.appendChild(statusMessageDiv);
    
    // Create SSE connection
    const eventSource = new EventSource(`/api/reservation-status?reservation_id=${reservation_id}`);
    
    // Track this connection globally so it can be closed when modal closes
    window.activeSSEConnections.push(eventSource);
    
    // Helper function to close and remove this connection from tracking
    const closeAndRemoveConnection = () => {
        eventSource.close();
        if (window.activeSSEConnections) {
            const index = window.activeSSEConnections.indexOf(eventSource);
            if (index > -1) {
                window.activeSSEConnections.splice(index, 1);
            }
        }
    };
    
    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            const paymentStatus = data.payment_status;
            const ticketStatus = data.ticket_status;
            
            console.log('Received status update:', data);
            
            // Update based on payment status
            if (paymentStatus.status === 'APPROVED') {
                updateStatusMessage(statusMessageDiv, 'approved', 'Payment approved! Your booking is confirmed.', reservation_id);
                // Close SSE connection after successful payment
                closeAndRemoveConnection();
            } else if (paymentStatus.status === 'REFUSED') {
                updateStatusMessage(statusMessageDiv, 'refused', 'Payment refused. Please try again with a different payment method.', reservation_id);
                // Close SSE connection after failed payment
                closeAndRemoveConnection();
            } else if (paymentStatus.status === 'PENDING') {
                updateStatusMessage(statusMessageDiv, 'processing', 'Processing payment... Please wait.', reservation_id);
            } else if (paymentStatus.status === 'error') {
                updateStatusMessage(statusMessageDiv, 'error', 'Error checking payment status. Please contact support.', reservation_id);
                closeAndRemoveConnection();
            }
            
        } catch (error) {
            console.error('Error parsing SSE data:', error);
        }
    };
    
    eventSource.onerror = function(event) {
        console.error('SSE connection error:', event);
        updateStatusMessage(statusMessageDiv, 'error', 'Connection error. Unable to check payment status.', reservation_id);
        closeAndRemoveConnection();
    };
    
    // Optional: Close connection after 5 minutes to prevent hanging connections
    setTimeout(() => {
        if (eventSource.readyState !== EventSource.CLOSED) {
            updateStatusMessage(statusMessageDiv, 'timeout', 'Status monitoring timed out. Please refresh to check status.', reservation_id);
            closeAndRemoveConnection();
        }
    }, 300000); // 5 minutes
}

/**
 * Updates the status message with appropriate styling
 * @param {HTMLElement} messageDiv - The div to update
 * @param {string} status - Status type: 'processing', 'approved', 'refused', 'error', 'timeout'
 * @param {string} message - The message to display
 * @param {string} reservation_id - The reservation ID
 */
function updateStatusMessage(messageDiv, status, message, reservation_id) {
    // Remove all existing status classes
    messageDiv.classList.remove(
        'bg-blue-100', 'text-blue-700', 'border-blue-200',
        'bg-green-100', 'text-green-700', 'border-green-200',
        'bg-red-100', 'text-red-700', 'border-red-200',
        'bg-gray-100', 'text-gray-700', 'border-gray-200'
    );
    
    // Add appropriate styling based on status
    switch (status) {
        case 'processing':
            messageDiv.classList.add('bg-blue-100', 'text-blue-700', 'border-blue-200');
            messageDiv.innerHTML = `
                <div class="flex items-center">
                    <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-700 mr-2"></div>
                    <span><strong>Reservation ${reservation_id}:</strong> ${message}</span>
                </div>
            `;
            break;
        case 'approved':
            messageDiv.classList.add('bg-green-100', 'text-green-700', 'border-green-200');
            messageDiv.innerHTML = `
                <div class="flex items-center">
                    <svg class="h-4 w-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
                    </svg>
                    <span><strong>Reservation ${reservation_id}:</strong> ${message}</span>
                </div>
            `;
            break;
        case 'refused':
            messageDiv.classList.add('bg-red-100', 'text-red-700', 'border-red-200');
            messageDiv.innerHTML = `
                <div class="flex items-center">
                    <svg class="h-4 w-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                    </svg>
                    <span><strong>Reservation ${reservation_id}:</strong> ${message}</span>
                </div>
            `;
            break;
        case 'error':
        case 'timeout':
            messageDiv.classList.add('bg-gray-100', 'text-gray-700', 'border-gray-200');
            messageDiv.innerHTML = `
                <div class="flex items-center">
                    <svg class="h-4 w-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
                    </svg>
                    <span><strong>Reservation ${reservation_id}:</strong> ${message}</span>
                </div>
            `;
            break;
    }
    
    // Add border styling
    messageDiv.classList.add('border');
}

// --- Event Listeners ---

// Event listener for Cruise Search Button
searchButton.addEventListener('click', async () => {
    const departure_harbor = departureHarborSelect.value;
    const arrival_harbor = arrivalHarborSelect.value;
    const departure_date = departureDateInput.value;

    if (!departure_harbor || !arrival_harbor || !departure_date) {
        showMessage('Please fill in all fields to search for cruises.');
        return;
    }

    try {
        const response = await axios.get('/api/cruises', {
            params: {
                departure_harbor: departure_harbor,
                arrival_harbor: arrival_harbor,
                departure_date: departure_date
            }
        });
        displayCruises(response.data);
    }
    catch (error) {
        console.error('Error searching for cruises:', error);
        if (error.response && error.response.data && error.response.data.error) {
            showMessage(`Error: ${error.response.data.error}`);
        } else {
            showMessage('Error connecting to the server or searching for cruises. Please try again later.');
        }
        resultsArea.innerHTML = '';
    }
});

// Event listener for Update Subscription Button
updateSubscriptionButton.addEventListener('click', async () => {
    const email = promotionEmailInput.value.trim();
    if (!email) {
        showMessage('Please enter an email to manage your subscription.', 'error');
        return;
    }

    if (subscribeCheckbox.checked) {
        // User wants to subscribe: directly connect SSE
        showMessage('Connecting to promotion stream...', 'info');
        connectSSE(email);
    } else {
        // User wants to unsubscribe: directly disconnect SSE
        disconnectSSE();
        showMessage('Unsubscription request sent. Disconnecting from stream...', 'info');
    }
});

// Event listener for checkbox state change (for convenience, also triggers update)
subscribeCheckbox.addEventListener('change', () => {
    // For now, it.
});

// Event listener for Confirm Booking Button
confirmBookingButton.addEventListener('click', async () => {
    const itinerary_id = currentBookingItineraryId; // Already a number from openBookingModal
    const num_passengers = parseInt(numPassengersInput.value, 10);
    const num_cabins = parseInt(numCabinsInput.value, 10);

    const cruise = fetchedCruisesMap.get(itinerary_id); // Use the numeric ID here

    // Client-side validation against remaining_passengers and remaining_cabinets
    if (num_passengers > cruise.remaining_passengers || num_cabins > cruise.remaining_cabinets) {
        showMessage('Booking quantity exceeds available capacity. Please adjust.', 'error', bookingResultArea);
        return;
    }

    if (!itinerary_id || isNaN(num_passengers) || num_passengers <= 0 || isNaN(num_cabins) || num_cabins <= 0) {
        showMessage('Please enter valid numbers for passengers and cabins.', 'error', bookingResultArea);
        return;
    }

    const total_price = cruise.price * num_passengers; // Calculate total price

    try {
        // Clear previous booking results/messages in the modal
        clearMessage(bookingResultArea);
        showMessage('Initiating booking...', 'info', bookingResultArea); // Indicate processing

        const response = await axios.post('/api/book-cruise', {
            itinerary_id,
            num_passengers,
            num_cabins,
            total_price // Include total_price in the payload
        });

        // Extract message, reservation_id, and payment_link from the response.data
        const { message, reservation_id, payment_link } = response.data;

        // Display initial booking success message and payment link
        showMessage(`Reservation Code: <span class="font-semibold">${reservation_id}</span>. Payment Link: <a href="${payment_link}" target="_blank" class="text-blue-600 hover:underline">Click Here</a>`, 'success', bookingResultArea);

        // Start SSE connection to monitor reservation status
        startReservationStatusMonitoring(reservation_id, bookingResultArea);

    } catch (error) {
        console.error('Error booking cruise:', error);
        if (error.response && error.response.data && error.response.data.error) {
            showMessage(`Error booking: ${error.response.data.error}`, 'error', bookingResultArea);
        } else {
            showMessage('Error communicating with the server to book cruise. Please try again later.', 'error', bookingResultArea);
        }
    }
});

// Event listener for Cancel Reservation Button
cancelReservationButton.addEventListener('click', async () => {
    const reservation_code = cancelReservationCodeInput.value.trim();

    if (!reservation_code) {
        showMessage('Please enter a reservation code to cancel.', 'error');
        return;
    }

    try {
        const response = await axios.post('/api/cancel-reservation', { reservation_code });
        showMessage(response.data.message, 'success');
        console.log('Cancellation response:', response.data.message);
        cancelReservationCodeInput.value = ''; // Clear input on success
    } catch (error) {
        console.error('Error cancelling reservation:', error);
        if (error.response && error.response.data && error.response.data.error) {
            showMessage(`Error cancelling: ${error.response.data.error}`, 'error');
        } else {
            showMessage('Error communicating with the server to cancel reservation. Please try again later.', 'error');
        }
    }
});


// Event listeners for modal close button and clicking outside the modal
closeButton.addEventListener('click', () => {
    // When modal closes, any active SSE connections will be automatically closed
    // by the closeBookingModal() function
    closeBookingModal();
});
window.addEventListener('click', (event) => {
    if (event.target === bookingModal) {
        // When modal closes, any active SSE connections will be automatically closed
        // by the closeBookingModal() function
        closeBookingModal();
    }
});


// --- Initial Setup ---

// Pre-fills the departure date with the current date when the page loads
document.addEventListener('DOMContentLoaded', () => {
    const today = new Date();
    const year = today.getFullYear();
    const month = (today.getMonth() + 1).toString().padStart(2, '0');
    const day = today.getDate().toString().padStart(2, '0');
    departureDateInput.value = `${year}-${month}-${day}`;

    // Initial state for promotions container
    promotionsContainer.innerHTML = `<p class="text-gray-600 text-center">Enter your email and check "Subscribe" to receive promotions.</p>`;
});
