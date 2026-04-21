/**
 * LearnBridge Screen Time Tracking Script
 * Automatically logs tool usage via heartbeat pings.
 */

(function () {
    const HEARTBEAT_INTERVAL = 30000; // 30 seconds
    let toolName = null;
    let courseId = null;

    window.LearnBridgeTracker = {
        init: function (config) {
            toolName = config.toolName;
            courseId = config.courseId || null;

            if (!toolName) {
                console.error('LearnBridgeTracker: toolName is required');
                return;
            }

            console.log(`LearnBridgeTracker: Initialized for ${toolName}`);

            // Start heartbeat
            setInterval(this.sendHeartbeat, HEARTBEAT_INTERVAL);

            // Send initial ping
            this.sendHeartbeat();
        },

        sendHeartbeat: function () {
            if (!toolName) return;

            const url = '/analytics/api/track-screen-time/';
            const data = {
                tool_name: toolName,
                course_id: courseId,
                duration: HEARTBEAT_INTERVAL / 1000
            };

            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': LearnBridgeTracker.getCookie('csrftoken')
                },
                body: JSON.stringify(data)
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // console.log('LearnBridgeTracker: Heartbeat successful');
                    } else {
                        console.error('LearnBridgeTracker: Heartbeat failed', data.message);
                    }
                })
                .catch(error => {
                    console.error('LearnBridgeTracker: Network error', error);
                });
        },

        getCookie: function (name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
    };
})();
