const list = document.querySelector("#orders");

async function loadOrders() {
  const response = await fetch("/orders");
  const orders = await response.json();
  const rows = orders.map(({ id }) => {
    const row = document.createElement("li");
    row.textContent = `Order ${id}`;
    return row;
  });
  list.replaceChildren(...rows);
}

loadOrders();
