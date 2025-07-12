import json
from pathlib import Path
from pydantic import BaseModel, Field
from .. import utils

class DocumentMetadata(BaseModel):
    id: str
    url: str
    title: str
    properties: dict

    #obsfucate is a method that hides the metadata of the document
    def obsfucate(self) -> 'DocumentMetadata': #proper obsfucation must be deep
        """Create an obfuscated version of this metadata by modifying in place.

        Returns:
            DocumentMetadata: Self, with ID and URL obfuscated.

        But why do so? --answer:
        Imagine you need to hide a person's identity.The Document object is the person.
        The DocumentMetadata object is the person's official ID card (like a driver's license or passport). 
        It contains their real name (id), home address (url), and other key facts.

        Now, let's look at the process:
        You want to hide the person. You give them a new alias. Let's say you change the Document's main id to a fake one.
        But what about their ID card? If you don't also change the name and address on their DocumentMetadata (their ID card), 
        then anyone who finds them can just look at the card and see their real identity. You've left a giant clue!
        """

        original_id = self.id.replace('-','') #remove the dashes from the id like 123-456-789 to 123456789
        fake_id = utils.generate_random_hex(length=32)

        #replace the original id with the fake id in the id and url
        self.id = fake_id
        self.url = self.url.replace(original_id,fake_id)

        return self #return the self object -> It's quite interesting why we are returning the self object
    
        #Reasoning : 

        # DESIGN PATTERN: FLUENT INTERFACE (METHOD CHAINING)
        # WHAT IT IS: A method that returns the object instance (`self`) after it has finished its task.
        # WHY USE IT: This pattern allows multiple methods to be called sequentially in a single line.
        #This way you don't pick the object again and again , you pick it once and then you call everything in one go , you don't put it down again and again

class Document(BaseModel):
    id: str = Field(default_factory=lambda: utils.generate_random_hex(length=32))
    metadata: DocumentMetadata
    parent_metadata: DocumentMetadata | None = None
    content: str
    content_quality_score: float|None = None
    summary: str|None = None
    child_urls: list[str] = Field(default_factory=list)

    #a class method, a type of factory method used to create an instance of the class from an external source.
    #it is a method that is bound to the class and not the instance of the class.
    #it ia used When you need to operate on or modify class-level attributes that should be shared across all instances.
    @classmethod
    def from_file(cls,file_path:Path): #Purpose: To deserialize(converting stored data into a format that can be used by the program) 
                                       # a Document object from a JSON file on disk.
        """Read a Document object from a JSON file.

        Args:
            file_path: Path to the JSON file containing document data.

        Returns:
            Document: A new Document instance constructed from the file data.

        Raises:
            FileNotFoundError: If the specified file doesn't exist.
            ValidationError: If the JSON data doesn't match the expected model structure.
        """
        json_data = file_path.read_text(encoding='utf-8')
        return cls.model_validate_json(json_data)
    
    #add_summary is a method that adds a summary to the document
    def add_summary(self,summary:str) -> 'Document':
        # Here, "Document" is in quotes because the class Document is not fully defined until the whole class block is finished.
        # And we are returning the self object , so we need to use quotes to refer to the class Document.
        self.summary = summary
        return self
    
    #add_quality_score is a method that adds a quality score to the document
    def add_quality_score(self,score:float) -> 'Document':
        self.content_quality_score = score
        return self
    
    # The key design choice here is returning the instance itself. This enables method chaining, allowing you to write concise code like:
    # doc.add_summary("A great document.").add_quality_score(0.95)

    # This method handles the serialization and writing of the document to the file system.
    def write(self,
            output_dir:Path,
            obsfucate:bool = False,
            also_save_as_txt:bool = False) -> None:
        """Write document data to file, optionally obfuscating sensitive information.

        Args:
            output_dir: Directory path where the files should be written.
            obfuscate: If True, sensitive information will be obfuscated.
            also_save_as_txt: If True, content will also be saved as a text file.
        """
        # Create the output directory if it doesn't exist
        output_dir.mkdir(parents=True,exist_ok=True)

        # Obfuscate the document if requested
        if obsfucate:
            self.obsfucate()

        json_page = self.model_dump() #convert the document object into a dictionary

        output_file = output_dir / f'{self.id}.json' #create a file with the id of the document
        with open(output_file,'w',encoding='utf-8') as f:
            json.dump(                  #Serializes the dictionary to a JSON string and writes it to the file.
                json_page,              #The dictionary to be serialized.
                f,
                indent=4,                #indent=4 makes the JSON human-readable
                ensure_ascii=False,      #ensure_ascii=False allows non-ASCII characters to be included in the output.
            )

        # Save the content as a text file if requested
        if also_save_as_txt:
            txt_path = output_file.with_suffix('.txt') #create a text file with the same name as the json file but with a .txt extension
            with open(txt_path,'w',encoding='utf-8') as f:
                f.write(self.content)

    def obsfucate(self) -> 'Document':
         """Create an obfuscated version of this document by modifying in place.

        Returns:
            Document: Self, with obfuscated metadata and parent_metadata.
        """
        #  Purpose: To hide or remove potentially sensitive data from the metadata and parent_metadata fields.

        self.metadata = self.metadata.obsfucate()
        self.parent_metadata = (
            self.parent_metadata.obsfucate() if self.parent_metadata else None
        )
        self.id = self.metadata.id
        return self

    #__eq__ is a method that compares two Document objects for equality.
    def __eq__(self,other:object) -> bool:
        """Compare two Document objects for equality.

        Args:
            other: Another object to compare with this Document.

        Returns:
            bool: True if the other object is a Document with the same ID.
        """
        # safety check to ensure that the other object is a Document object
        if not isinstance(other, Document):
            return False
        # equality based only on the id field.
        return self.id == other.id
    
    #hash is a method that generates a hash value for the document
    def __hash__(self) -> int:
        """Generate a hash value for the Document.

        Returns:
            int: Hash value based on the document's ID.
        """
        return hash(self.id)



