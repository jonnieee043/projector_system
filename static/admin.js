
const table = document.getElementById("projector-table");
const message = document.getElementById("admin-message");

function showMessage(text, isError = false) {
    message.textContent = text;
    message.style.color = isError ? "#c0392b" : "#16834a";
}


function formatDate(value) {
    if (!value) return "N/A";

    const date = new Date(value + "T00:00:00");

    return date.toLocaleDateString("en-PH", {
        year: "numeric",
        month: "short",
        day: "numeric"
    });
}


async function loadProjectors() {
    try {
        const response = await fetch("/api/projectors");
        const projectors = await response.json();

        if (!response.ok) {
            throw new Error(projectors.error || "Unable to load records.");
        }

        table.innerHTML = "";

        let available = 0;
        let borrowed = 0;

        projectors.forEach(projector => {
            const isAvailable = projector.availability === "Available";

            if (isAvailable) {
                available++;
            } else {
                borrowed++;
            }

            const row = document.createElement("tr");

            const values = [
                projector.id,
                projector.name,
                projector.availability,
                formatDate(projector.date_borrowed),
                formatDate(projector.date_returned),
                projector.borrowed_by || "N/A"
            ];

            values.forEach((value, index) => {
                const cell = document.createElement("td");
                cell.textContent = value;

                if (index === 2) {
                    cell.className = isAvailable
                        ? "status-available"
                        : "status-borrowed";
                }

                row.appendChild(cell);
            });

            const actions = document.createElement("td");
            actions.className = "action-buttons";

            if (isAvailable) {
                const borrowButton = document.createElement("button");

                borrowButton.textContent = "Borrow";
                borrowButton.onclick = () => borrowProjector(projector.id);

                actions.appendChild(borrowButton);

            } else {
                const returnButton = document.createElement("button");

                returnButton.textContent = "Return";
                returnButton.onclick = () => returnProjector(projector.id);

                actions.appendChild(returnButton);
            }

            const editButton = document.createElement("button");

            editButton.textContent = "Edit";
            editButton.className = "edit-button";
            editButton.onclick = () => editProjector(projector);

            actions.appendChild(editButton);

            const deleteButton = document.createElement("button");

            deleteButton.textContent = "Delete";
            deleteButton.className = "delete-button";
            deleteButton.onclick = () => deleteProjector(projector.id);

            actions.appendChild(deleteButton);

            row.appendChild(actions);
            table.appendChild(row);
        });

        document.getElementById("total-count").textContent = projectors.length;
        document.getElementById("available-count").textContent = available;
        document.getElementById("borrowed-count").textContent = borrowed;

    } catch (error) {
        showMessage(error.message, true);
    }
}


async function borrowProjector(id) {
    const borrower = prompt("Enter the borrower's name:");

    if (!borrower || !borrower.trim()) {
        return;
    }

    try {
        const response = await fetch(`/api/projectors/${id}/borrow`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                borrowed_by: borrower.trim()
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Borrow failed.");
        }

        showMessage(data.message);
        await loadProjectors();

    } catch (error) {
        showMessage(error.message, true);
    }
}


async function returnProjector(id) {
    if (!confirm("Confirm that this projector has been returned?")) {
        return;
    }

    try {
        const response = await fetch(`/api/projectors/${id}/return`, {
            method: "POST"
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Return failed.");
        }

        showMessage(data.message);
        await loadProjectors();

    } catch (error) {
        showMessage(error.message, true);
    }
}


async function editProjector(projector) {
    const name = prompt("Enter the projector name:", projector.name);

    if (!name || !name.trim()) {
        return;
    }

    try {
        const response = await fetch(`/api/projectors/${projector.id}/edit`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                name: name.trim()
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Update failed.");
        }

        showMessage(data.message);
        await loadProjectors();

    } catch (error) {
        showMessage(error.message, true);
    }
}


async function deleteProjector(id) {
    if (!confirm("Are you sure you want to delete this projector?")) {
        return;
    }

    try {
        const response = await fetch(`/api/projectors/${id}`, {
            method: "DELETE"
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Delete failed.");
        }

        showMessage(data.message);
        await loadProjectors();

    } catch (error) {
        showMessage(error.message, true);
    }
}


loadProjectors();
