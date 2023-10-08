-- MySQL dump 10.13  Distrib 8.0.32, for Win64 (x86_64)
--
-- Host: localhost    Database: webgpt
-- ------------------------------------------------------
-- Server version	8.0.32

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `products`
--

DROP TABLE IF EXISTS `products`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `products` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `price` decimal(10,2) NOT NULL,
  `description` text,
  `sku` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=27 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `products`
--

LOCK TABLES `products` WRITE;
/*!40000 ALTER TABLE `products` DISABLE KEYS */;
INSERT INTO `products` VALUES (1,'Samsung Galaxy S21',799.99,'A flagship smartphone from Samsung.','SKU123'),(2,'Apple iPhone 13',999.99,'The latest iPhone model.','SKU456'),(3,'Google Pixel 6',699.99,'A high-quality Android smartphone.','SKU789'),(4,'Sony PlayStation 5',499.99,'A next-gen gaming console.','SKU101'),(5,'Dell XPS 13',1199.99,'A powerful laptop for professionals.','SKU202'),(6,'Premium Leather Wallet',49.99,'A sleek and stylish leather wallet with multiple card slots and compartments.','WAL123'),(7,'Wireless Bluetooth Earbuds',39.99,'High-quality wireless earbuds with noise-cancellation technology and long battery life.','EB123'),(8,'Stainless Steel Water Bottle',14.99,'Durable and eco-friendly water bottle that keeps beverages hot or cold for hours.','WB234'),(9,'Fitness Tracker Watch',59.99,'A smartwatch with fitness tracking features, heart rate monitor, and smartphone connectivity.','SW456'),(10,'Portable Power Bank',24.99,'Compact power bank for charging devices on the go, with multiple charging ports.','PB567'),(11,'Laptop Backpack',39.99,'Stylish and functional backpack designed to carry laptops and other essentials.','BP678'),(12,'Smart Home Security Camera',59.99,'Wi-Fi-enabled security camera with motion detection and two-way audio.','CAM789'),(13,'Retro Polaroid Camera',69.99,'Vintage-style instant camera for capturing and printing memories in an instant.','PIC890'),(14,'Insulated Travel Mug',19.99,'Travel-friendly mug that keeps beverages hot or cold during your commute.','TM123'),(15,'Wireless Charging Pad',29.99,'Convenient wireless charging pad for smartphones and other Qi-compatible devices.','CP234'),(16,'Noise-Canceling Headphones',89.99,'Premium headphones with active noise cancellation and immersive sound.','HP345'),(17,'Elegant Wrist Watch',79.99,'Sophisticated wrist watch with a classic design and precision timekeeping.','WW456'),(18,'Smart Home Speaker',79.99,'Voice-controlled smart speaker with built-in virtual assistant and high-quality audio.','SP567'),(19,'Portable Bluetooth Speaker',29.99,'Compact and portable speaker for wirelessly streaming music and podcasts.','BS678'),(20,'Professional DSLR Camera',799.99,'High-performance DSLR camera for professional-level photography and videography.','CAM789'),(21,'Gourmet Coffee Grinder',49.99,'Grind your own coffee beans for a fresh and flavorful cup of coffee every time.','CG890'),(22,'Air Purifier',129.99,'HEPA air purifier that removes allergens and pollutants, ensuring clean and fresh indoor air.','AP123'),(23,'Yoga Mat',19.99,'Non-slip yoga mat for comfortable and safe yoga practice at home or in the studio.','YM234'),(24,'Stylish Sunglasses',29.99,'Fashionable sunglasses with UV protection and polarized lenses for a clear view.','SG345'),(25,'Digital Drawing Tablet',149.99,'Graphic drawing tablet for digital artists and illustrators to create stunning artworks.','DT456'),(26,'Smart Thermostat',89.99,'Wi-Fi-enabled thermostat for efficient home climate control and energy savings.','ST567');
/*!40000 ALTER TABLE `products` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2023-08-24 16:08:57
