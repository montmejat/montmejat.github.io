(() => {
    // Function to apply the theme
    const applyTheme = (themeValue) => {
        document.body.setAttribute('data-bs-theme', themeValue);
        // Update any other elements or classes as needed for the theme
    };

    // Function to load and apply the saved theme
    const loadAndApplyTheme = () => {
        const savedTheme = sessionStorage.getItem('theme');
        if (savedTheme) {
            applyTheme(savedTheme);
            // Update the dropdown to show the active theme
            document.querySelectorAll('.dropdown-item').forEach(item => {
                if (item.getAttribute('data-bs-theme-value') === savedTheme) {
                    item.classList.add('active');
                    item.setAttribute('aria-pressed', 'true');
                } else {
                    item.classList.remove('active');
                    item.setAttribute('aria-pressed', 'false');
                }
            });
        }
        // Make the body visible after theme is applied
        document.body.style.visibility = 'visible'; // or use document.body.style.display = 'block';
    };

    // Load and apply the saved theme on page load
    loadAndApplyTheme();

    // Add event listeners to the dropdown items for theme change
    document.querySelectorAll('.dropdown-item').forEach(item => {
        item.addEventListener('click', function () {
            const themeValue = this.getAttribute('data-bs-theme-value');
            applyTheme(themeValue); // Apply the theme

            // Save the selected theme for persistence
            sessionStorage.setItem('theme', themeValue);

            // Update the active state for the dropdown items
            document.querySelectorAll('.dropdown-item').forEach(item => {
                item.classList.remove('active');
                item.setAttribute('aria-pressed', 'false');
            });
            this.classList.add('active');
            this.setAttribute('aria-pressed', 'true');
        });
    });
})();
