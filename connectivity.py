import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import json
import os
import threading


class RelationshipMapper:
    def __init__(self, root):
        self.root = root
        self.root.title("Relationship Mapper")
        self.network = nx.Graph()
        self.relationships = {}
        self.data_file = "relationships.json"
        self.auto_save_interval = 300  #Auto-saves every 5 minutes

        self.load_data()
        self.setup_gui()
        self.start_auto_save()

    def setup_gui(self):
        #Adding a Person Section
        self.name_label = ttk.Label(self.root, text="Name:")
        self.name_label.grid(row=0, column=0, padx=5, pady=5)
        self.name_entry = ttk.Entry(self.root)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)

        self.add_button = ttk.Button(self.root, text="Add Person", command=self.add_person)
        self.add_button.grid(row=0, column=2, padx=5, pady=5)

        self.rename_button = ttk.Button(self.root, text="Rename Person", command=self.rename_person)
        self.rename_button.grid(row=0, column=4, padx=5, pady=5)

        #Remove Person Section
        self.remove_button = ttk.Button(self.root, text="Remove Person", command=self.remove_person)
        self.remove_button.grid(row=0, column=3, padx=5, pady=5)

        #Search Bar
        self.search_label = ttk.Label(self.root, text="Search:")
        self.search_label.grid(row=1, column=0, padx=5, pady=5)
        self.search_entry = ttk.Entry(self.root)
        self.search_entry.grid(row=1, column=1, padx=5, pady=5)
        self.search_entry.bind("<KeyRelease>", self.search_people)

        #List of People
        self.people_listbox = tk.Listbox(self.root, height=10, selectmode=tk.SINGLE)
        self.people_listbox.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky="ew")
        self.people_listbox.bind('<<ListboxSelect>>', self.open_person_gui)

        #Map and File Operations
        self.map_button = ttk.Button(self.root, text="Generate Map", command=self.generate_map)
        self.map_button.grid(row=3, column=0, padx=5, pady=10)

        self.export_button = ttk.Button(self.root, text="Export Data", command=self.export_data)
        self.export_button.grid(row=3, column=1, padx=5, pady=10)

        self.import_button = ttk.Button(self.root, text="Import Data", command=self.import_data)
        self.import_button.grid(row=3, column=2, padx=5, pady=10)

        #Status Bar
        self.status_bar = ttk.Label(self.root, text="Welcome to Relationship Mapper!", anchor="w")
        self.status_bar.grid(row=4, column=0, columnspan=4, sticky="we", padx=5, pady=5)

        self.refresh_people_listbox()

    def set_status(self, message):
        self.status_bar.config(text=message)

    def refresh_people_listbox(self, query=""):
        self.people_listbox.delete(0, tk.END)
        for person in self.network.nodes:
            if query.lower() in person.lower():
                self.people_listbox.insert(tk.END, person)

    def add_person(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Name cannot be empty!")
            return

        if name in self.network:
            messagebox.showwarning("Warning", f"{name} is already in the network.")
            return

        self.network.add_node(name)
        if name not in self.relationships:
            self.relationships[name] = {}  #Initialize an empty relationship dictionary
        self.refresh_people_listbox()
        self.name_entry.delete(0, tk.END)
        self.set_status(f"{name} added to the network.")
        self.save_data()

    def rename_person(self):
        for i in self.relationships:
            print(i)
        selected = self.people_listbox.curselection()

        if not selected:
            messagebox.showerror("Error", "No person selected!")
            return

        old_name = self.people_listbox.get(selected)

        check = 0
        for i in self.relationships:
            if i==old_name:
                check = 1
                break
        if check == 1:
            pass
        elif check != 1:
            messagebox.showerror("Error", f"Person '{old_name}' does not exist in the network.")
            return


        new_name = simpledialog.askstring("Rename Person", f"Enter new name for {old_name}:")
        if not new_name:
            messagebox.showwarning("Warning", "No new name provided. Renaming cancelled.")
            return

        newcheck = 0
        for i in self.relationships:
            if i==new_name:
                newcheck = 1
                break
        if newcheck == 1:
            messagebox.showerror("Error", f"Person '{new_name}' already exists in the network.")
            return
        elif newcheck != 1:
            pass

        #Renames the person in the network
        self.network = nx.relabel_nodes(self.network, {old_name: new_name})

        #Renames the key in the relationships dictionary
        self.relationships[new_name] = self.relationships.pop(old_name)

        #Updates relationships for other nodes and checks both directions of the given relationships
        for person, rels in list(self.relationships.items()):
            updated_rels = {}
            for related_person, status in rels.items():
                if related_person == old_name:
                    updated_rels[new_name] = status  #Updates old name to new name
                else:
                    updated_rels[related_person] = status
            self.relationships[person] = updated_rels

        #Ensures updated relationships in reverse direction too
        for u, v, data in self.network.edges(data=True):
            if u == old_name or v == old_name:
                status = data["status"]
                self.network[u][v]["status"] = status  #Updates relationships in the graph

        #Refreshes UI
        self.refresh_people_listbox()
        self.set_status(f"Renamed '{old_name}' to '{new_name}'.")

        self.save_data()

    def remove_person(self):
        selected = self.people_listbox.curselection()
        if not selected:
            messagebox.showerror("Error", "No person selected!")
            return

        name = self.people_listbox.get(selected)
        self.network.remove_node(name)
        del self.relationships[name]
        for rel in self.relationships.values():
            if name in rel:
                del rel[name]

        self.refresh_people_listbox()
        self.set_status(f"{name} removed from the network.")
        self.save_data()

    def open_person_gui(self, event):
        selected = self.people_listbox.curselection()
        if not selected:
            return

        name = self.people_listbox.get(selected)
        PersonEditor(self.root, name, self.relationships, self.network, self.save_data, self.set_status)

    def search_people(self, event):
        query = self.search_entry.get().strip()
        self.refresh_people_listbox(query)

    def generate_map(self):
        pos = nx.spring_layout(self.network)
        colors = {
            "Friend": "green",
            "Dislike": "red",
            "Together": "pink",
            "Exes": "black",
            "Best Friends": "blue",
            "Complicated": "orange",
            "Situationship": "yellow",
            "Acquaintances": "lightblue",
            "Likes": "purple",
            "Distant": "gray"
        }

        #Creates a figure for the map
        fig, ax = plt.subplots(figsize=(12, 8))  #Increases width to accommodate the legend

        #Sets the default sizes and colors for all nodes and edges
        self.node_sizes = {node: 500 for node in self.network.nodes}  #Default size for all nodes
        self.node_colors = {node: "lightgray" for node in self.network.nodes}  #Default color for all nodes
        self.edge_widths = [1] * len(self.network.edges())  #Default width for all edges
        self.edge_colors = [
            colors.get(data["status"], "black") for u, v, data in self.network.edges(data=True)
        ]

        #Draws the graph initially with normal relationships and no special selection
        nx.draw_networkx(self.network, pos, ax=ax, with_labels=True, node_size=list(self.node_sizes.values()),
                         node_color=list(self.node_colors.values()), edge_color=self.edge_colors,
                         width=self.edge_widths)

        #Creates axes for the legend outside the connectivity map
        legend_ax = fig.add_axes([0.85, 0.1, 0.12, 0.8])  #Positions the legend to the right of the graph

        #Adds a semi-transparent legend with colored boxes
        box_size = 0.02  #Size of the color boxes
        spacing = 0.04  #Vertical spacing between legend entries
        legend_x = 0.5  #X-coordinate of the boxes within the legend axis
        legend_y = 1  #Starting Y-coordinate at the top

        #Turns off the axis of the legend (no ticks or grid)
        legend_ax.axis('off')

        #Adds colored boxes and their labels in the legend
        for i, (label, color) in enumerate(colors.items()):
            #Adds a colored rectangle (legend box)
            legend_ax.add_patch(plt.Rectangle((legend_x - box_size / 2, legend_y - i * spacing),
                                              box_size, box_size, color=color))

            #Adds the label next to the color box
            legend_ax.text(legend_x + box_size / 2 + 0.01, legend_y - i * spacing, label, fontsize=10, va='center')

        #Tracks the currently selected node
        self.selected_node = None

        def on_click(event):
            min_dist = float('inf')
            closest_node = None

            #Gets current axis limits to preserve zoom and panning
            xlim, ylim = ax.get_xlim(), ax.get_ylim()

            for node, coord in pos.items():
                dist = (event.xdata - coord[0]) ** 2 + (event.ydata - coord[1]) ** 2
                if dist < min_dist:
                    min_dist = dist
                    closest_node = node

            if closest_node:
                if closest_node == self.selected_node:
                    #Unselects the node without resetting zoom/pan
                    self.selected_node = None
                    #Resets node sizes and colors
                    self.node_sizes = {node: 500 for node in self.network.nodes}
                    self.node_colors = {node: "lightgray" for node in self.network.nodes}
                    self.edge_widths = [1] * len(self.network.edges)
                    self.edge_colors = [colors.get(data["status"], "black") for u, v, data in
                                        self.network.edges(data=True)]

                    #Resets the relationships for all nodes when the node is unclicked
                    self.edge_widths = [1] * len(self.network.edges)
                    self.edge_colors = [colors.get(data["status"], "black") for u, v, data in
                                        self.network.edges(data=True)]

                else:
                    #Selects the new node
                    self.selected_node = closest_node
                    self.node_sizes = {node: 500 for node in self.network.nodes}
                    self.node_sizes[closest_node] = 1000
                    self.node_colors = {node: "lightgray" for node in self.network.nodes}
                    self.node_colors[closest_node] = "yellow"
                    self.edge_widths = []
                    self.edge_colors = []
                    for u, v, data in self.network.edges(data=True):
                        if u == closest_node or v == closest_node:
                            self.edge_widths.append(3)
                            self.edge_colors.append(colors.get(data["status"], "green"))
                        else:
                            self.edge_widths.append(1)
                            self.edge_colors.append("lightgray")

                #Clears the axis and redraw the network without changing zoom/pan
                ax.clear()
                nx.draw_networkx(self.network, pos, ax=ax, with_labels=True, node_size=list(self.node_sizes.values()),
                                 node_color=list(self.node_colors.values()), edge_color=self.edge_colors,
                                 width=self.edge_widths)

                #Restores the axis limits (zoom and pan stay the same)
                ax.set_xlim(xlim)
                ax.set_ylim(ylim)

                plt.title("Relationship Map")
                plt.axis("off")
                plt.draw()

        def reset_graph(ax, pos):
            self.node_sizes = {node: 500 for node in self.network.nodes}
            self.node_colors = {node: "lightgray" for node in self.network.nodes}
            self.edge_widths = [1] * len(self.network.edges())
            self.edge_colors = [colors.get(data["status"], "black") for u, v, data in self.network.edges(data=True)]
            ax.clear()
            nx.draw_networkx(self.network, pos, ax=ax, with_labels=True, node_size=list(self.node_sizes.values()),
                             node_color=list(self.node_colors.values()), edge_color=self.edge_colors,
                             width=self.edge_widths)
            plt.title("Relationship Map")
            plt.axis("off")
            plt.draw()

        fig.canvas.mpl_connect("button_press_event", on_click)

        #Reset button
        reset_ax = fig.add_axes([0.8, 0.05, 0.1, 0.075])
        reset_button = Button(reset_ax, 'Reset')

        def on_reset(event):
            self.selected_node = None
            reset_graph(ax, pos)

        reset_button.on_clicked(on_reset)

        def on_scroll(event):
            #Zooms in or out based on scroll direction
            scale_factor = 1.1
            if event.button == 'up':
                factor = scale_factor
            elif event.button == 'down':
                factor = 1 / scale_factor
            else:
                return

            xlim, ylim = ax.get_xlim(), ax.get_ylim()

            #Gets the position of the mouse cursor on the canvas
            mouse_x, mouse_y = event.x, event.y

            #Converts the mouse cursor position to data coordinates (the same as the graph)
            ax_pos = ax.transData.inverted().transform((mouse_x, mouse_y))

            #Zooms in or out by changing axis limits
            new_xlim = [x * factor for x in xlim]
            new_ylim = [y * factor for y in ylim]

            #Finds the difference between the mouse position and the center of the plot
            delta_x = ax_pos[0] - (xlim[0] + xlim[1]) / 2
            delta_y = ax_pos[1] - (ylim[0] + ylim[1]) / 2

            #Applies the zoom but adjusts the center based on the mouse cursor's position
            ax.set_xlim([x + delta_x * (1 - factor) for x in new_xlim])
            ax.set_ylim([y + delta_y * (1 - factor) for y in new_ylim])

            plt.draw()

        fig.canvas.mpl_connect("scroll_event", on_scroll)

        #Arrow key panning (move the graph)
        def on_key(event):
            xlim, ylim = ax.get_xlim(), ax.get_ylim()
            pan_factor = 0.1 * (xlim[1] - xlim[0])  #Adjust pan factor based on zoom level


            if event.key == 'up':
                ax.set_ylim([y + pan_factor for y in ylim])
            elif event.key == 'down':
                ax.set_ylim([y - pan_factor for y in ylim])
            elif event.key == 'left':
                ax.set_xlim([x - pan_factor for x in xlim])
            elif event.key == 'right':
                ax.set_xlim([x + pan_factor for x in xlim])

            plt.draw()

        fig.canvas.mpl_connect("key_press_event", on_key)

        plt.title("Relationship Map")
        plt.axis("off")
        plt.show()

    def export_data(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if not file_path:
            return

        nodes = list(self.network.nodes)
        edges = []

        #Adds relationships in both directions
        for u, v, data in self.network.edges(data=True):
            status = data["status"]
            edges.append([u, v, status])  #Original direction
            edges.append([v, u, status])  #Reverse direction (both directions)

        #Saves nodes and edges to a JSON file
        with open(file_path, "w") as f:
            json.dump({"nodes": nodes, "edges": edges}, f)

        self.set_status("Data exported successfully!")

    def import_data(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not file_path:
            return

        with open(file_path, "r") as f:
            data = json.load(f)

        self.network.clear()
        self.relationships.clear()

        self.network.add_nodes_from(data["nodes"])
        for u, v, status in data["edges"]:
            self.network.add_edge(u, v, status=status)
            if u not in self.relationships:
                self.relationships[u] = {}
            self.relationships[u][v] = status

        self.refresh_people_listbox()
        self.set_status("Data imported successfully!")
        self.save_data()

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as f:
                data = json.load(f)
                self.network.add_nodes_from(data["nodes"])
                for u, v, status in data["edges"]:
                    self.network.add_edge(u, v, status=status)
                    if u not in self.relationships:
                        self.relationships[u] = {}
                    self.relationships[u][v] = status

    def save_data(self):
        nodes = list(self.network.nodes)
        edges = [(u, v, data["status"]) for u, v, data in self.network.edges(data=True)]
        with open(self.data_file, "w") as f:
            json.dump({"nodes": nodes, "edges": edges}, f)

    def start_auto_save(self):
        def auto_save():
            while True:
                self.save_data()
                threading.Event().wait(self.auto_save_interval)

        threading.Thread(target=auto_save, daemon=True).start()


class PersonEditor:
    def __init__(self, root, name, relationships, network, save_callback, status_callback):
        self.root = tk.Toplevel(root)
        self.root.title(f"Edit Relationships for {name}")
        self.name = name
        self.relationships = relationships
        self.network = network
        self.save_callback = save_callback
        self.status_callback = status_callback
        self.filtered_people = sorted([person for person in self.network.nodes if person != self.name])  #Sorted list of other people

        self.setup_gui()

    def setup_gui(self):
        self.relationships_label = ttk.Label(self.root, text=f"Relationships for {self.name}")
        self.relationships_label.grid(row=0, column=0, columnspan=2, pady=10)

        self.relation_frame = ttk.Frame(self.root)
        self.relation_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5)

        #Adds scrollable area for relationships
        self.canvas = tk.Canvas(self.relation_frame, height=200)  #Set desired height
        self.scrollbar = ttk.Scrollbar(self.relation_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        #Inputs fields for adding relationships
        self.relation_combobox = ttk.Combobox(self.root, state="normal")
        self.relation_combobox.grid(row=2, column=0, padx=5, pady=5)
        self.relation_combobox.bind("<KeyRelease>", self.update_relation_combobox)
        self.update_relation_combobox()  #Initializes the dropdown

        self.status_combobox = ttk.Combobox(
            self.root,
            values=["Friend", "Dislike", "Together", "Exes", "Best Friends",
                    "Complicated", "Situationship", "Acquaintances", "Likes", "Distant"],
            state="readonly"
        )
        self.status_combobox.grid(row=2, column=1, padx=5, pady=5)

        self.add_relation_button = ttk.Button(self.root, text="Add/Update Relationship",
                                              command=self.add_or_update_relationship)
        self.add_relation_button.grid(row=3, column=0, columnspan=2, pady=5)

        self.refresh_relations()

    def update_relation_combobox(self, event=None):
        """Update the combobox dropdown with filtered values based on user input."""
        query = self.relation_combobox.get().lower()  #Gets current input
        self.filtered_people = [person for person in self.network.nodes if person != self.name and query in person.lower()]
        self.relation_combobox['values'] = self.filtered_people

    def refresh_relations(self):
        #Clears the existing relations
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        #Gets all relationships for the selected person
        all_relations = self.relationships.get(self.name, {})

        for person, relation in all_relations.items():
            label = ttk.Label(self.scrollable_frame, text=f"{person}: {relation}")
            label.grid(sticky="w", padx=5, pady=2)

        #Includes relationships for the selected person that involve others
        for person in self.filtered_people:
            if person != self.name:
                for related_person, relation in self.relationships.get(person, {}).items():
                    if related_person == self.name:
                        label = ttk.Label(self.scrollable_frame, text=f"{person}: {relation}")
                        label.grid(sticky="w", padx=5, pady=2)

    def add_or_update_relationship(self):
        person = self.relation_combobox.get().strip()
        status = self.status_combobox.get().strip()
        if not person or not status:
            messagebox.showerror("Error", "Both person and status must be selected!")
            return

        if person not in self.network.nodes:
            messagebox.showerror("Error", f"{person} does not exist in the network!")
            return

        if self.name not in self.relationships:
            self.relationships[self.name] = {}
        self.relationships[self.name][person] = status

        self.network.add_edge(self.name, person, status=status)
        self.refresh_relations()
        self.save_callback()
        self.status_callback(f"Relationship with {person} ({status}) updated!")

    def remove_relationship(self, person):
        del self.relationships[self.name][person]
        if not self.relationships[self.name]:
            del self.relationships[self.name]
        self.network.remove_edge(self.name, person)
        self.refresh_relations()
        self.save_callback()
        self.status_callback(f"Relationship with {person} removed.")


if __name__ == "__main__":
    root = tk.Tk()
    app = RelationshipMapper(root)
    root.mainloop()







