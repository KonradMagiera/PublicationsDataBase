package clientjavafx;

import java.io.IOException;
import javafx.application.Application;
import javafx.fxml.FXMLLoader;
import javafx.scene.Scene;
import javafx.scene.layout.GridPane;
import javafx.stage.Stage;
import view.MainController;


public class ClientJavaFX extends Application {

    @Override
    public void start(Stage primaryStage)  throws IOException{
        FXMLLoader loader = new FXMLLoader(this.getClass().getResource("/clientjavafx/fxml/mainlayout.fxml"));;
	GridPane pane = loader.load();
	Scene scene = new Scene(pane);
        primaryStage.setTitle("Publications");
        primaryStage.setScene(scene);
        primaryStage.setResizable(true);
        primaryStage.show();
    }

    public static void main(String[] args) {
        launch(args);
    }
}
