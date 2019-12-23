package view;

import clientjavafx.ClientJavaFX;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.MalformedURLException;
import java.net.URL;
import java.util.ResourceBundle;
import java.util.logging.Level;
import java.util.logging.Logger;
import javafx.event.ActionEvent;
import javafx.fxml.FXML;
import javafx.fxml.FXMLLoader;
import javafx.fxml.Initializable;
import javafx.scene.Scene;
import javafx.scene.layout.Pane;

public class MainController implements Initializable {

    @FXML
    private Pane display;

    @Override
    public void initialize(URL url, ResourceBundle rb){
        try {
            FXMLLoader loader = new FXMLLoader(this.getClass().getResource("/clientjavafx/fxml/login.fxml"));;
            Pane pane = loader.load();
            display.getChildren().add(pane);
        } catch (IOException ex) {
            System.out.println("Jakiś błąd");
        }
    }

    @FXML
    private void showPublications(ActionEvent event) {
    }

    @FXML
    private void logout(ActionEvent event) {

    }

//    private static String convertStreamToString(InputStream is) {
//
//        BufferedReader reader = new BufferedReader(new InputStreamReader(is));
//        StringBuilder sb = new StringBuilder();
//
//        String line = null;
//        try {
//            while ((line = reader.readLine()) != null) {
//                sb.append(line + "\n");
//            }
//        } catch (IOException e) {
//            e.printStackTrace();
//        } finally {
//            try {
//                is.close();
//            } catch (IOException e) {
//                e.printStackTrace();
//            }
//        }
//        return sb.toString();
//    }
//
//    private void request() {
//        try {
//            System.out.println("Hello World!");
//            HttpURLConnection connection = (HttpURLConnection) new URL("http://192.168.99.100:5000/login").openConnection();
//            connection.setDoOutput(true);
//            connection.setRequestMethod("POST");
//
//            // JWT generate
//            connection.setRequestProperty("Authorization", "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VybmFtZSI6ImFkbWluIiwicGFzc3dvcmQiOiJhZG1pbiIsImV4cCI6MTU3NzE1MjU2MX0.aMxM0HbnIm_V_sw42OZh7BqgJAiWZop97VF6menfp0c");
//            InputStream response = connection.getInputStream();
//            String responseMsg = convertStreamToString(response);
//            System.out.println(responseMsg);
//        } catch (MalformedURLException ex) {
//            System.out.println("1111111111111");
//            Logger.getLogger(ClientJavaFX.class.getName()).log(Level.SEVERE, null, ex);
//        } catch (IOException ex) {
//            System.out.println("2222222222");
//            Logger.getLogger(ClientJavaFX.class.getName()).log(Level.SEVERE, null, ex);
//        }
//
//    }
}
