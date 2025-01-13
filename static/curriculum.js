const curriculum = {
    K1: {
        topics: [
            "Counting",
            "Plants",
            "Alphabet",
            "Family",
            "Basics",
            "Drawing",
            "Movement"
        ]
    },
    K2: {
        topics: [
            "Shapes",
            "Animals",
            "Phonics",
            "Community",
            "Typing",
            "Coloring",
            "Fitness"
        ]
    },
    K3: {
        topics: [
            "Addition",
            "Weather",
            "Reading",
            "Maps",
            "Computers",
            "Painting",
            "Games"
        ]
    },
    K4: {
        topics: [
            "Subtraction",
            "Photosynthesis",
            "Writing",
            "History",
            "Coding",
            "Music",
            "Sports"
        ]
    },
    K5: {
        topics: [
            "Multiplication",
            "Cells",
            "Grammar",
            "Government",
            "Software",
            "Sculpture",
            "Athletics"
        ]
    },
    K6: {
        topics: [
            "Fractions",
            "Genetics",
            "Comprehension",
            "Geography",
            "Hardware",
            "Theater",
            "Coordination"
        ]
    },
    K7: {
        topics: [
            "Geometry",
            "Osmosis",
            "Literature",
            "Civics",
            "Programming",
            "Dance",
            "Endurance"
        ]
    },
    K8: {
        topics: [
            "Algebra",
            "Ecology",
            "Vocabulary",
            "Culture",
            "Robotics",
            "Photography",
            "Agility"
        ]
    },
    K9: {
        topics: [
            "Trigonometry",
            "Evolution",
            "Composition",
            "Economics",
            "Cybersecurity",
            "Digital Art",
            "Strength"
        ]
    }
};

function handleAIResponse(response) {
    if (response.type === "lesson_start") {
        displayMessage(response.message);
    } else if (response.type === "lesson_intro") {
        displayMessage(response.message);
        if (response.question) {
            displayQuestion(response.question);
        }
    } else if (response.type === "invalid_answer") {
        displayMessage(response.message);
        if (response.question) {
            displayQuestion(response.question);
        }
    } else if (response.type === "feedback") {
        displayMessage(response.message);
    } else if (response.type === "next_lesson") {
        displayMessage(response.message);
    } else if (response.type === "completion") {
        displayMessage(response.message);
    } else {
        displayMessage(response.message);
    }
}

function displayQuestion(questionText) {
    const lines = questionText.split('\n');
    const question = lines[0].replace('Q: ', '');
    const options = lines.slice(1).map(line => {
        const [key, value] = line.split(') ');
        return { key: key.trim(), value: value.trim() };
    });
    
    const cardContainer = document.getElementById('card-container');
    cardContainer.innerHTML = '';
    
    const questionElement = document.createElement('div');
    questionElement.className = 'question';
    questionElement.innerText = question;
    cardContainer.appendChild(questionElement);
    
    options.forEach(option => {
        const button = document.createElement('button');
        button.className = 'option-button';
        button.innerText = `${option.key}) ${option.value}`;
        button.onclick = () => handleOptionClick(option.key);
        cardContainer.appendChild(button);
    });
}

function handleOptionClick(selectedOption) {
    // Send the selected option to the backend
    sendAnswer(selectedOption);
    
    // Disable all buttons to prevent multiple submissions
    const buttons = document.querySelectorAll('.option-button');
    buttons.forEach(button => button.disabled = true);
}

async function sendAnswer(selectedOption) {
    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ message: selectedOption }),
        });

        const data = await response.json();
        handleAIResponse(data.response);
        chatBox.scrollTop = chatBox.scrollHeight;
    } catch (error) {
        addMessage("system", "Sorry, there was an error processing your request.");
    } finally {
        document.querySelector('.loading-animation').classList.add('hidden');
    }
}

export default curriculum;