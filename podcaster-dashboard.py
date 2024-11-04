import json
import sys
from collections import defaultdict
from string import Template
import os

class MyTemplate(Template):
    delimiter = '@'

if len(sys.argv) < 2:
    print("Usage: python generate_dashboard.py <boosts.json> [output.html]")
    sys.exit(1)

json_filename = sys.argv[1]

if len(sys.argv) >= 3:
    output_filename = sys.argv[2]
else:
    base_name = os.path.splitext(json_filename)[0]
    output_filename = f"{base_name}.html"

with open(json_filename, 'r', encoding='utf-8') as f:
    data = json.load(f)

boosts = []

for invoice in data['invoices']:
    # Filter invoices that start with "keysend" and have status "paid"
    if invoice['label'].startswith('keysend') and invoice['status'] == 'paid':
        # Parse the description field (which is another JSON)
        try:
            description_str = invoice['description'].replace('keysend: ', '')
            boost_details = json.loads(description_str)
        except json.JSONDecodeError:
            continue

        boost = {
            'timestamp': invoice['paid_at'],
            'podcast': boost_details.get('podcast', ''),
            'episode': boost_details.get('episode', ''),
            'sender': boost_details.get('sender_name', ''),
            'message': boost_details.get('message', ''),
            'value': int(invoice['amount_received_msat']) / 1000  # Convert msat to sat
        }
        boosts.append(boost)

boosts.sort(key=lambda x: x['timestamp'], reverse=True)

# Collect unique podcasts and episodes for the selection boxes
# Create a mapping from podcast to its episodes
podcast_episode_map = defaultdict(set)
for boost in boosts:
    if boost['episode']:
        podcast_episode_map[boost['podcast']].add(boost['episode'])

podcasts = sorted(podcast_episode_map.keys())

html_template = '''
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <title>Podcasting 2.0 Boosts Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {
            background-color: #0c0c0d;
            color: #f0f0f0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }
        h1 {
            color: #ffffff;
        }
        .container {
            max-width: 1200px;
        }
        table {
            border-collapse: collapse;
            width: 100%;
        }
        th, td {
            border-bottom: 1px solid #323234;
        }
        th {
            background-color: #1b1b1c;
            color: #a9a9ad;
        }
        td {
            color: #e2e2e2;
            text-align: left;
            padding: 12px 8px;
        }
        .truncate {
            max-width: 150px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .rounded {
            border-radius: 8px;
        }
        tr:hover {
            background-color: #202023;
        }
        .sender {
            max-width: 150px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        input[type="checkbox"] {
            accent-color: #444;
        }
        @@media screen and (max-width: 768px) {  /* Notice the @@ escape */
            .container {
                padding: 16px;
            }
            .table-fixed th, .table-fixed td {
                font-size: 12px;
            }
        }
    </style>
</head>
<body>
    <div class="container mx-auto p-4">
        <h1 class="text-3xl font-bold mb-4">Podcasting 2.0 Boosts Dashboard</h1>

        <div class="flex space-x-4 mb-4">
            <div class="w-1/3">
                <label for="podcast-select" class="block text-sm font-medium">Filter by Podcast</label>
                <select id="podcast-select" class="mt-1 block w-full bg-gray-800 border border-gray-600 text-white py-2 px-3 rounded-md">
                    <option value="">All Podcasts</option>
                    @podcast_options
                </select>
            </div>
            <div class="w-1/3">
                <label for="episode-select" class="block text-sm font-medium">Filter by Episode</label>
                <select id="episode-select" class="mt-1 block w-full bg-gray-800 border border-gray-600 text-white py-2 px-3 rounded-md">
                    <option value="">All Episodes</option>
                </select>
            </div>
            <div class="w-1/3 flex items-center">
                <input id="only-messages" type="checkbox" class="h-4 w-4 bg-gray-800 border-gray-600 rounded-md">
                <label for="only-messages" class="ml-2 block text-sm font-medium">Only Messages</label>
            </div>
        </div>

        <div id="sum-container" class="mb-4 text-lg text-gray-400"></div>

        <table class="min-w-full bg-gray-800 table-fixed rounded-lg">
            <thead>
                <tr>
                    <th class="w-40 px-4 py-3 text-left font-medium text-sm">Date</th>
                    <th class="w-40 px-4 py-3 text-left font-medium text-sm">Podcast</th>
                    <th class="w-40 px-4 py-3 text-left font-medium text-sm">Episode</th>
                    <th class="w-40 px-4 py-3 text-left font-medium text-sm">Sender</th>
                    <th class="px-4 py-3 text-left font-medium text-sm">Message</th>
                    <th class="w-32 px-4 py-3 text-right font-medium text-sm">Value (sats)</th>
                </tr>
            </thead>
            <tbody id="boosts-table">
                <!-- Table rows will be inserted here by JavaScript -->
            </tbody>
        </table>
    </div>

    <script>
        let boosts = @boosts_json;
        const podcastSelect = document.getElementById('podcast-select');
        const episodeSelect = document.getElementById('episode-select');
        const onlyMessagesCheckbox = document.getElementById('only-messages');
        const boostsTable = document.getElementById('boosts-table');
        let currentSortKey = 'timestamp';
        let sortAscending = false;

        // Group boosts without messages from the same user for the same episode
        boosts = boosts.reduce((acc, boost) => {
            // If the boost has a message, keep it as is
            if (boost.message && boost.message.trim()) {
                acc.push(boost);
                return acc;
            }

            // Look for an existing boost from the same user for the same episode without a message
            const existingBoost = acc.find(b =>
                !b.message &&  // No message
                b.sender === boost.sender &&  // Same sender
                b.podcast === boost.podcast &&  // Same podcast
                b.episode === boost.episode  // Same episode
            );

            if (existingBoost) {
                // Update the existing boost
                existingBoost.value += boost.value;
                // Update timestamp to the latest one
                if (boost.timestamp > existingBoost.timestamp) {
                    existingBoost.timestamp = boost.timestamp;
                }
            } else {
                // Add as a new boost
                acc.push(boost);
            }

            return acc;
        }, []);

        const podcastEpisodeMap = {};
        boosts.forEach(boost => {
            if (!podcastEpisodeMap[boost.podcast]) {
                podcastEpisodeMap[boost.podcast] = new Set();
            }
            podcastEpisodeMap[boost.podcast].add(boost.episode);
        });

        function updateEpisodeOptions() {
            const selectedPodcast = podcastSelect.value;
            let boostsToConsider = boosts;

            if (selectedPodcast !== '') {
                boostsToConsider = boostsToConsider.filter(boost => boost.podcast === selectedPodcast);
            }

            // Build a mapping of episodes to their latest boost timestamp
            const episodeMap = new Map();

            boostsToConsider.forEach(boost => {
                const episode = boost.episode;
                if (episode && episode.trim() !== '') {
                    const timestamp = boost.timestamp;
                    if (!episodeMap.has(episode) || episodeMap.get(episode) < timestamp) {
                        episodeMap.set(episode, timestamp);
                    }
                }
            });

            // Convert the map to an array and sort by latest timestamp descending
            const episodes = Array.from(episodeMap.entries())
                .map(([name, timestamp]) => ({ name, timestamp }))
                .sort((a, b) => b.timestamp - a.timestamp);

            episodeSelect.innerHTML = '<option value="">All Episodes</option>';
            episodes.forEach(episode => {
                const option = document.createElement('option');
                option.value = episode.name;
                option.textContent = episode.name;
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
                if (selectedPodcast && boost.podcast !== selectedPodcast) match = false;
                if (selectedEpisode && boost.episode !== selectedEpisode) match = false;
                if (onlyMessages && (!boost.message || !boost.message.trim())) match = false;
                return match;
            });

            filteredBoosts.sort((a, b) => {
                let compare = a[currentSortKey] < b[currentSortKey] ? -1 : 1;
                return sortAscending ? compare : -compare;
            });


            boostsTable.innerHTML = filteredBoosts.map(boost => `
                <tr class="border-b border-gray-700">
                    <td class="px-4 py-3">${new Date(boost.timestamp * 1000).toLocaleString()}</td>
                    <td class="px-4 py-3 truncate" title="${boost.podcast}">${boost.podcast}</td>
                    <td class="px-4 py-3 truncate" title="${boost.episode}">${boost.episode}</td>
                    <td class="px-4 py-3 sender" title="${boost.sender}">${boost.sender}</td>
                    <td class="px-4 py-3">${boost.message || ''}</td>
                    <td class="px-4 py-3 text-right">${boost.value}</td>
                </tr>
            `).join('');

            updateSums();
        }

        podcastSelect.addEventListener('change', () => { updateEpisodeOptions(); renderTable(); });
        episodeSelect.addEventListener('change', renderTable);
        onlyMessagesCheckbox.addEventListener('change', renderTable);

        updateEpisodeOptions();
        renderTable();
    </script>
</body>
</html>
'''

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
