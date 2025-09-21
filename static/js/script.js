document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('vehicle-search');
  const searchBtn = document.getElementById('search-btn');
  const vehicles = document.querySelectorAll('.vehicle-card');

  // Function to filter vehicles
  function filterVehicles() {
    const searchTerm = searchInput.value.toLowerCase().trim();
    if (searchTerm === "") {
      // Show all if search is empty
      vehicles.forEach(vehicle => vehicle.style.display = 'block');
      return;
    }

    // Split search into keywords
    const keywords = searchTerm.split(/\s+/);

    vehicles.forEach(vehicle => {
      const title = vehicle.querySelector('h3').textContent.toLowerCase();
      const description = vehicle.querySelector('p').textContent.toLowerCase();

      // Check if any keyword matches title or description
      const matches = keywords.some(keyword => title.includes(keyword) || description.includes(keyword));

      vehicle.style.display = matches ? 'block' : 'none';
    });
  }

  // Live search as user types
  searchInput.addEventListener('input', filterVehicles);

  // Also filter when search button is clicked
  searchBtn.addEventListener('click', filterVehicles);
});
