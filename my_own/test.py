"""Program entry point."""

import sys
from Colors import Colors
from Graph import Graph
from GraphBuilder import GraphBuilder
from Parser import Parser
from Simulation import Simulation
from Dijkstra import Dijkstra
from Validator import Validator


def main() -> None:
    """Parse input and run the simulation."""
    try:
        Validator.check_all(sys.argv)
        parser: Parser = Parser(sys.argv[1])
        parser.parse()
        graph_builder: GraphBuilder = GraphBuilder(parser)
        graph: Graph = graph_builder.create()
        simulation = Simulation(graph, Dijkstra)
        simulation.run()
    except BaseException as error:
        print(f"{Colors.RED}{error}")


if __name__ == "__main__":
    main()
