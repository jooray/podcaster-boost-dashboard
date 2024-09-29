import json
import sys
from collections import defaultdict
from string import Template
import os

# Define a custom Template class with a different delimiter
class MyTemplate(Template):
    delimiter = '@'

# Get the JSON file name from command-line arguments
if len(sys.argv) < 2:
    print("Usage: python generate_dashboard.py <boosts.json> [output.html]")
    sys.exit(1)

json_filename = sys.argv[1]

# Determine the output HTML file name
if len(sys.argv) >= 3:
    output_filename = sys.argv[2]
else:
    # Replace .json extension with .html
    base_name = os.path.splitext(json_filename)[0]
    output_filename = f"{base_name}.html"

# Load the JSON data from the specified file
with open(json_filename, 'r', encoding='utf-8') as f:
    data = json.load(f)

boosts = []

# Process the invoices
for invoice in data['invoices']:
    # Filter invoices that start with "keysend" and have status "paid"
    if invoice['label'].startswith('keysend') and invoice['status'] == 'paid':
        # Parse the description field (which is another JSON)
        try:
            description_str = invoice['description'].replace('keysend: ', '')
            boost_details = json.loads(description_str)
        except json.JSONDecodeError:
            continue  # Skip if description is not valid JSON

        # Extract the relevant details
        boost = {
            'timestamp': invoice['paid_at'],
            'podcast': boost_details.get('podcast', ''),
            'episode': boost_details.get('episode', ''),
            'sender': boost_details.get('sender_name', ''),
            'message': boost_details.get('message', ''),
            'value': int(invoice['amount_received_msat']) / 1000  # Convert msat to sat
        }
        boosts.append(boost)

# Sort the boosts by timestamp descending (newest first)
boosts.sort(key=lambda x: x['timestamp'], reverse=True)

# Collect unique podcasts and episodes for the selection boxes
# Create a mapping from podcast to its episodes
podcast_episode_map = defaultdict(set)
for boost in boosts:
    podcast_episode_map[boost['podcast']].add(boost['episode'])

podcasts = sorted(podcast_episode_map.keys())

# Generate the HTML
html_template = '''
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <title>Podcasting 2.0 Boosts Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-white">
    <div class="container mx-auto p-4">
        <h1 class="text-3xl font-bold mb-4">Podcasting 2.0 Boosts Dashboard</h1>

        <div class="flex space-x-4 mb-4">
            <div>
                <label for="podcast-select" class="block text-sm font-medium text-gray-300">Filter by Podcast</label>
                <select id="podcast-select" class="mt-1 block w-full bg-gray-800 border border-gray-700 text-white py-2 px-3 rounded">
                    <option value="">All Podcasts</option>
                    @podcast_options
                </select>
            </div>
            <div>
                <label for="episode-select" class="block text-sm font-medium text-gray-300">Filter by Episode</label>
                <select id="episode-select" class="mt-1 block w-full bg-gray-800 border border-gray-700 text-white py-2 px-3 rounded">
                    <option value="">All Episodes</option>
                    <!-- Episode options will be populated dynamically -->
                </select>
            </div>
            <div class="flex items-center">
                <input id="only-messages" type="checkbox" class="h-4 w-4 text-blue-600 bg-gray-800 border-gray-700 rounded">
                <label for="only-messages" class="ml-2 block text-sm font-medium text-gray-300">Only Messages</label>
            </div>
        </div>

        <!-- Sum Container -->
        <div id="sum-container" class="mb-4 text-lg text-gray-300">
            <!-- Sums will be displayed here -->
        </div>

        <table class="min-w-full bg-gray-800 rounded">
            <thead>
                <tr>
                    <th class="px-6 py-3 text-left text-sm font-medium text-gray-300 uppercase tracking-wider cursor-pointer" onclick="sortTable('timestamp')">Date</th>
                    <th class="px-6 py-3 text-left text-sm font-medium text-gray-300 uppercase tracking-wider cursor-pointer" onclick="sortTable('podcast')">Podcast</th>
                    <th class="px-6 py-3 text-left text-sm font-medium text-gray-300 uppercase tracking-wider cursor-pointer" onclick="sortTable('episode')">Episode</th>
                    <th class="px-6 py-3 text-left text-sm font-medium text-gray-300 uppercase tracking-wider cursor-pointer" onclick="sortTable('sender')">Sender</th>
                    <th class="px-6 py-3 text-left text-sm font-medium text-gray-300 uppercase tracking-wider">Message</th>
                    <th class="px-6 py-3 text-left text-sm font-medium text-gray-300 uppercase tracking-wider cursor-pointer" onclick="sortTable('value')">Value (sats)</th>
                </tr>
            </thead>
            <tbody id="boosts-table">
                <!-- Table rows will be inserted here by JavaScript -->
            </tbody>
        </table>
    </div>

    <script>
        const boosts = @boosts_json;

        const podcastSelect = document.getElementById('podcast-select');
        const episodeSelect = document.getElementById('episode-select');
        const onlyMessagesCheckbox = document.getElementById('only-messages');
        const boostsTable = document.getElementById('boosts-table');

        let currentSortKey = 'timestamp';
        let sortAscending = false;

        // Build a mapping from podcast to episodes
        const podcastEpisodeMap = {};
        boosts.forEach(boost => {
            if (!podcastEpisodeMap[boost.podcast]) {
                podcastEpisodeMap[boost.podcast] = new Set();
            }
            podcastEpisodeMap[boost.podcast].add(boost.episode);
        });

        function updateEpisodeOptions() {
            const selectedPodcast = podcastSelect.value;
            let episodes = new Set();

            if (selectedPodcast === '') {
                // If no podcast selected, include all episodes
                boosts.forEach(boost => episodes.add(boost.episode));
            } else {
                // Get episodes for the selected podcast
                episodes = podcastEpisodeMap[selectedPodcast] || new Set();
            }

            // Clear existing options
            episodeSelect.innerHTML = '<option value="">All Episodes</option>';

            // Add new options
            Array.from(episodes).sort().forEach(episode => {
                const option = document.createElement('option');
                option.value = episode;
                option.textContent = episode;
                episodeSelect.appendChild(option);
            });
        }

        function updateSums() {
            const sumContainer = document.getElementById('sum-container');
            const selectedPodcast = podcastSelect.value;
            const selectedEpisode = episodeSelect.value;

            let podcastSum = 0;
            let episodeSum = 0;
            let sumHtml = '';

            if (selectedPodcast !== '') {
                // Sum all boosts matching the selected podcast
                podcastSum = boosts
                    .filter(boost => boost.podcast === selectedPodcast)
                    .reduce((sum, boost) => sum + boost.value, 0);

                sumHtml += `<div>Total sats for podcast "<strong>${selectedPodcast}</strong>": <strong>${podcastSum}</strong></div>`;
            }

            if (selectedEpisode !== '') {
                // Sum all boosts matching the selected episode
                episodeSum = boosts
                    .filter(boost => boost.episode === selectedEpisode)
                    .reduce((sum, boost) => sum + boost.value, 0);

                sumHtml += `<div>Total sats for episode "<strong>${selectedEpisode}</strong>": <strong>${episodeSum}</strong></div>`;
            }

            sumContainer.innerHTML = sumHtml;
        }

        function renderTable() {
            const selectedPodcast = podcastSelect.value;
            const selectedEpisode = episodeSelect.value;
            const onlyMessages = onlyMessagesCheckbox.checked;

            let filteredBoosts = boosts.filter(boost => {
                let match = true;
                if (selectedPodcast !== '' && boost.podcast !== selectedPodcast) {
                    match = false;
                }
                if (selectedEpisode !== '' && boost.episode !== selectedEpisode) {
                    match = false;
                }
                if (onlyMessages) {
                    const msg = boost.message ? boost.message.trim() : '';
                    if (msg === '' || msg === '.' || msg === '-') {
                        match = false;
                    }
                }
                return match;
            });

            // Sort the boosts
            filteredBoosts.sort((a, b) => {
                let compare = 0;
                if (a[currentSortKey] < b[currentSortKey]) compare = -1;
                if (a[currentSortKey] > b[currentSortKey]) compare = 1;
                return sortAscending ? compare : -compare;
            });

            // Generate table rows
            boostsTable.innerHTML = filteredBoosts.map(boost => `
                <tr class="border-b border-gray-700">
                    <td class="px-6 py-4 whitespace-nowrap">${new Date(boost.timestamp * 1000).toLocaleString()}</td>
                    <td class="px-6 py-4 whitespace-nowrap">${boost.podcast}</td>
                    <td class="px-6 py-4 whitespace-nowrap">${boost.episode}</td>
                    <td class="px-6 py-4 whitespace-nowrap">${boost.sender}</td>
                    <td class="px-6 py-4 whitespace-wrap">${boost.message || ''}</td>
                    <td class="px-6 py-4 whitespace-nowrap">${boost.value}</td>
                </tr>
            `).join('');

            // Update sums
            updateSums();
        }

        function sortTable(key) {
            if (currentSortKey === key) {
                sortAscending = !sortAscending;
            } else {
                currentSortKey = key;
                sortAscending = true;
            }
            renderTable();
        }

        podcastSelect.addEventListener('change', () => {
            updateEpisodeOptions();
            renderTable();
        });

        episodeSelect.addEventListener('change', renderTable);
        onlyMessagesCheckbox.addEventListener('change', renderTable);

        // Initial population of episode options
        updateEpisodeOptions();

        renderTable();
    </script>
</body>
</html>
'''

# Generate options for podcast select
podcast_options = '\n'.join(f'<option value="{p}">{p}</option>' for p in podcasts)

# Prepare the boosts data for JavaScript
import json as json_module  # Avoid conflict with imported json
boosts_json = json_module.dumps(boosts)

# Fill in the template using the custom MyTemplate class
html_content = MyTemplate(html_template).substitute(
    podcast_options=podcast_options,
    boosts_json=boosts_json
)

# Write the HTML content to the output file
with open(output_filename, 'w', encoding='utf-8') as f:
    f.write(html_content)
